# RTL register-stage inventory collector for the kdebug Tcl NPI backend.
#
# This file is sourced by kdebug_npi.tcl after the Verdi design is loaded.  It
# intentionally contains no package dependencies so it also works with the
# Tcl 8.5 runtime shipped by Verdi O-2018.09-SP2.

namespace eval ::rscheck_inventory {
    variable default_trace_depth 16
    variable maximum_trace_depth 256
    variable maximum_scope_depth 256
    variable maximum_object_visits 100000
    variable maximum_object_stack_depth 1024
    variable state_sequence 0

    variable warnings
    array set warnings {}
    variable trace_unresolved
    array set trace_unresolved {}
    variable trace_depth_limited
    array set trace_depth_limited {}
    variable trace_object_visits
    array set trace_object_visits {}
    variable trace_diagnostics
    array set trace_diagnostics {}
    variable trace_diagnostic_seen
    array set trace_diagnostic_seen {}
    variable trace_best_object_depth
    array set trace_best_object_depth {}
    variable trace_expanded_module_depth
    array set trace_expanded_module_depth {}
    variable trace_modules
    array set trace_modules {}
}

proc ::rscheck_inventory::env_value {name default_value} {
    if {[info exists ::env($name)] && $::env($name) ne ""} {
        return $::env($name)
    }
    return $default_value
}

proc ::rscheck_inventory::read_text_file {path label} {
    if {$path eq ""} {
        error "$label file path is required"
    }
    if {[catch {set fp [open $path r]} message]} {
        error "cannot open $label file: $path: $message"
    }
    fconfigure $fp -translation binary -encoding utf-8
    if {[catch {set text [read $fp]} message]} {
        catch {close $fp}
        error "cannot read $label file: $path: $message"
    }
    if {[catch {close $fp} message]} {
        error "cannot close $label file: $path: $message"
    }
    return $text
}

proc ::rscheck_inventory::read_positions {path} {
    set text [read_text_file $path "positions"]
    array set seen {}
    set positions {}
    foreach raw [split $text "\n"] {
        set position [string trim $raw " \t\r"]
        if {$position eq "" || [info exists seen($position)]} {
            continue
        }
        set seen($position) 1
        lappend positions $position
    }
    if {[llength $positions] == 0} {
        error "positions file contains no non-empty hierarchy paths: $path"
    }
    return [lsort -ascii $positions]
}

proc ::rscheck_inventory::read_trace_rules {path} {
    set rules [dict create]
    if {$path eq ""} {
        return $rules
    }
    set text [read_text_file $path "trace rules"]
    set line_number 0
    foreach raw [split $text "\n"] {
        incr line_number
        set line [string trimright $raw "\r"]
        if {[string trim $line " \t"] eq ""} {
            continue
        }
        set pieces [split $line "\t"]
        if {[llength $pieces] != 2} {
            error "trace rules line $line_number must contain exactly module<TAB>clock_port"
        }
        set module [string trim [lindex $pieces 0] " \t\r"]
        set clock_port [string trim [lindex $pieces 1] " \t\r"]
        if {$module eq "" || $clock_port eq ""} {
            error "trace rules line $line_number has an empty module or clock port"
        }
        if {[dict exists $rules $module] && [dict get $rules $module] ne $clock_port} {
            error "trace rules define conflicting clock ports for module $module"
        }
        dict set rules $module $clock_port
    }
    return $rules
}

proc ::rscheck_inventory::parse_trace_depth {text} {
    variable default_trace_depth
    variable maximum_trace_depth
    if {$text eq ""} {
        return $default_trace_depth
    }
    if {![string is integer -strict $text] || $text < 1 || $text > $maximum_trace_depth} {
        error "trace max depth must be an ASCII integer from 1 to $maximum_trace_depth"
    }
    return $text
}

proc ::rscheck_inventory::add_warning {message} {
    variable warnings
    if {$message ne ""} {
        set warnings($message) 1
    }
}

proc ::rscheck_inventory::language_string {handle property} {
    if {$handle eq ""} {return ""}
    if {[catch {npi_get_str -property $property -object $handle} value]} {
        return ""
    }
    return $value
}

proc ::rscheck_inventory::language_integer {handle property} {
    if {$handle eq ""} {return ""}
    if {[catch {npi_get -property $property -object $handle} value]} {
        return ""
    }
    return $value
}

proc ::rscheck_inventory::netlist_string {handle property} {
    if {$handle eq ""} {return ""}
    if {[catch {npi_nl_get_str -property $property -object $handle} value]} {
        return ""
    }
    return $value
}

proc ::rscheck_inventory::release_language {handle} {
    if {$handle ne ""} {
        catch {npi_release_handle -object $handle}
    }
}

proc ::rscheck_inventory::release_netlist {handle} {
    if {$handle ne ""} {
        catch {npi_nl_release_handle -object $handle}
    }
}

proc ::rscheck_inventory::language_key {handle} {
    set type [language_string $handle npiType]
    set name [language_string $handle npiFullName]
    if {$name eq ""} {set name [language_string $handle npiName]}
    if {$name eq ""} {set name $handle}
    return "$type\x1f$name"
}

proc ::rscheck_inventory::netlist_key {handle} {
    set type [netlist_string $handle npiNlType]
    set name [netlist_string $handle npiNlFullName]
    if {$name eq ""} {set name [netlist_string $handle npiNlName]}
    if {$name eq ""} {set name $handle}
    return "$type\x1f$name"
}

proc ::rscheck_inventory::query_top_instances {} {
    set names {}
    array set seen {}
    if {[catch {set iterator [npi_iterate -type npiInstance -refHandle ""]}]} {
        return $names
    }
    if {$iterator eq ""} {return $names}
    while {1} {
        if {[catch {set top [npi_scan -iterator $iterator]}]} {break}
        if {$top eq ""} {break}
        set name [language_string $top npiFullName]
        if {$name ne "" && ![info exists seen($name)]} {
            set seen($name) 1
            lappend names $name
        }
        release_language $top
    }
    return [lsort -ascii $names]
}

proc ::rscheck_inventory::resolve_ref_object {handle state_id} {
    set current $handle
    for {set depth 0} {$current ne "" && $depth < 32} {incr depth} {
        if {[language_string $current npiType] ne "npiRefObj"} {
            return $current
        }
        if {[catch {set actual [npi_handle -type npiActual -refHandle $current]}]} {
            set actual ""
        }
        if {$actual eq ""} {return $current}
        release_language $current
        set current $actual
    }
    if {$current ne "" && [language_string $current npiType] eq "npiRefObj"} {
        set full_name [language_string $current npiFullName]
        set message "npiRefObj resolution exceeded the depth limit at $full_name"
        if {$state_id eq ""} {
            add_warning $message
        } else {
            mark_trace_unresolved $state_id $message
        }
    }
    return $current
}

proc ::rscheck_inventory::decompile_object {handle} {
    set text [language_string $handle npiDecompile]
    if {$text ne ""} {return $text}
    if {[llength [info commands ::npi_L1::npi_expr_decompile]]} {
        if {![catch {set text [::npi_L1::npi_expr_decompile $handle]}] && $text ne ""} {
            return $text
        }
    }
    return ""
}

proc ::rscheck_inventory::read_high_connection {port {state_id ""}} {
    set info [dict create connection "" object_type "" full_name "" direction ""]
    dict set info full_name [language_string $port npiFullName]
    set direction [language_string $port npiDirection]
    if {$direction eq "npiInput" || $direction eq "npiOutput" || $direction eq "npiInout"} {
        dict set info direction $direction
    }
    if {[catch {set connection [npi_handle -type npiHighConn -refHandle $port]}]} {
        set connection ""
    }
    if {$connection eq ""} {return $info}
    set connection [resolve_ref_object $connection $state_id]
    dict set info object_type [language_string $connection npiType]
    set name [language_string $connection npiFullName]
    if {$name eq ""} {set name [decompile_object $connection]}
    if {$name eq ""} {set name [language_string $connection npiName]}
    dict set info connection $name
    release_language $connection
    return $info
}

proc ::rscheck_inventory::merge_port {ports_var port instance_full_name {state_id ""}} {
    upvar 1 $ports_var ports
    if {$port eq ""} {return}
    set name [language_string $port npiName]
    if {$name eq ""} {
        set message "NPI port is missing its name in module instance: $instance_full_name"
        if {$state_id eq ""} {add_warning $message} else {mark_trace_unresolved $state_id $message}
        return
    }
    set info [read_high_connection $port $state_id]
    if {![dict exists $ports $name]} {
        dict set ports $name $info
        return
    }
    set existing [dict get $ports $name]
    foreach field {connection object_type full_name direction} {
        if {[dict get $existing $field] eq "" && [dict get $info $field] ne ""} {
            dict set existing $field [dict get $info $field]
        }
    }
    dict set ports $name $existing
}

proc ::rscheck_inventory::collect_ports {module instance_full_name {state_id ""}} {
    set ports [dict create]
    if {![catch {set iterator [npi_iterate -type npiPort -refHandle $module]}] && $iterator ne ""} {
        while {1} {
            if {[catch {set port [npi_scan -iterator $iterator]}]} {break}
            if {$port eq ""} {break}
            merge_port ports $port $instance_full_name $state_id
            release_language $port
        }
    }
    if {$instance_full_name ne "" && [llength [info commands ::npi_L1::npi_mod_inst_get_port]]} {
        set fallback_ports {}
        if {![catch {::npi_L1::npi_mod_inst_get_port $instance_full_name fallback_ports}]} {
            foreach port $fallback_ports {
                if {$port eq ""} {continue}
                merge_port ports $port $instance_full_name $state_id
                release_language $port
            }
        }
    }
    return $ports
}

proc ::rscheck_inventory::parameter_value {parameter} {
    if {$parameter eq ""} {return [list 0 ""]}
    if {[catch {set value [npi_get_value -format npiBinStrVal -object $parameter]}]} {
        return [list 0 ""]
    }
    if {$value eq "NPI_GET_VALUE_ERROR_STR"} {
        return [list 0 ""]
    }
    return [list 1 $value]
}

proc ::rscheck_inventory::merge_parameter {parameters_var parameter instance_full_name} {
    upvar 1 $parameters_var parameters
    if {$parameter eq ""} {return}
    set name [language_string $parameter npiName]
    if {$name eq ""} {
        add_warning "NPI parameter is missing its name in module instance: $instance_full_name"
        return
    }
    set value_info [parameter_value $parameter]
    if {![dict exists $parameters $name]} {
        dict set parameters $name $value_info
        return
    }
    set existing [dict get $parameters $name]
    if {![lindex $existing 0] && [lindex $value_info 0]} {
        dict set parameters $name $value_info
    }
}

proc ::rscheck_inventory::collect_parameters {module instance_full_name} {
    set parameters [dict create]
    if {![catch {set iterator [npi_iterate -type npiParameter -refHandle $module]}] && $iterator ne ""} {
        while {1} {
            if {[catch {set parameter [npi_scan -iterator $iterator]}]} {break}
            if {$parameter eq ""} {break}
            merge_parameter parameters $parameter $instance_full_name
            release_language $parameter
        }
    }
    if {$instance_full_name ne "" && [llength [info commands ::npi_L1::npi_mod_inst_get_parameter]]} {
        set fallback_parameters {}
        if {![catch {::npi_L1::npi_mod_inst_get_parameter $instance_full_name fallback_parameters}]} {
            foreach parameter $fallback_parameters {
                if {$parameter eq ""} {continue}
                merge_parameter parameters $parameter $instance_full_name
                release_language $parameter
            }
        }
    }
    return $parameters
}

proc ::rscheck_inventory::new_trace_state {} {
    variable state_sequence
    variable trace_unresolved
    variable trace_depth_limited
    variable trace_object_visits
    variable trace_diagnostics
    incr state_sequence
    set state_id $state_sequence
    set trace_unresolved($state_id) 0
    set trace_depth_limited($state_id) 0
    set trace_object_visits($state_id) 0
    set trace_diagnostics($state_id) {}
    return $state_id
}

proc ::rscheck_inventory::state_index {state_id key} {
    return "$state_id\x1e$key"
}

proc ::rscheck_inventory::add_trace_diagnostic {state_id message} {
    variable trace_diagnostics
    variable trace_diagnostic_seen
    set index [state_index $state_id $message]
    if {![info exists trace_diagnostic_seen($index)]} {
        set trace_diagnostic_seen($index) 1
        lappend trace_diagnostics($state_id) $message
    }
}

proc ::rscheck_inventory::mark_trace_unresolved {state_id message} {
    variable trace_unresolved
    set trace_unresolved($state_id) 1
    add_trace_diagnostic $state_id $message
}

proc ::rscheck_inventory::begin_trace_object {state_id handle module_depth} {
    variable maximum_object_visits
    variable trace_object_visits
    variable trace_best_object_depth
    set key [netlist_key $handle]
    set index [state_index $state_id $key]
    if {[info exists trace_best_object_depth($index)] &&
        $trace_best_object_depth($index) <= $module_depth} {
        return 0
    }
    if {$trace_object_visits($state_id) >= $maximum_object_visits} {
        mark_trace_unresolved $state_id "clock trace exceeded the $maximum_object_visits Netlist object budget"
        return 0
    }
    set trace_best_object_depth($index) $module_depth
    incr trace_object_visits($state_id)
    return 1
}

proc ::rscheck_inventory::owning_instance {inst_port} {
    if {[catch {set instance [npi_nl_handle -type npiNlInst -refHandle $inst_port]}]} {
        set instance ""
    }
    if {$instance ne ""} {return $instance}
    if {[netlist_string $inst_port npiNlType] ne "npiNlPseudoInstPort"} {
        return ""
    }
    if {[catch {set actual [npi_nl_handle -type npiNlParent -refHandle $inst_port]}]} {
        set actual ""
    }
    if {$actual eq ""} {return ""}
    if {[catch {set instance [npi_nl_handle -type npiNlInst -refHandle $actual]}]} {
        set instance ""
    }
    release_netlist $actual
    return $instance
}

proc ::rscheck_inventory::module_hit_from_instance {instance state_id} {
    set full_name [netlist_string $instance npiNlFullName]
    if {$full_name eq ""} {set full_name [netlist_string $instance npiNlName]}
    set module [netlist_string $instance npiNlDefName]
    if {$full_name eq "" || $module eq ""} {
        mark_trace_unresolved $state_id "NPI Netlist module driver is missing its instance or definition name"
        return ""
    }
    return [list $full_name $module]
}

proc ::rscheck_inventory::append_netlist_relation {stack_var relation handle module_depth stack_depth {net_only 0}} {
    upvar 1 $stack_var stack
    if {[catch {set iterator [npi_nl_iterate -type $relation -refHandle $handle]}] || $iterator eq ""} {
        return
    }
    while {1} {
        if {[catch {set child [npi_nl_scan -iterator $iterator]}]} {break}
        if {$child eq ""} {break}
        if {$net_only} {
            set child_type [netlist_string $child npiNlType]
            if {$child_type ne "npiNlDeclNet" &&
                $child_type ne "npiNlConcatNet" &&
                $child_type ne "npiNlSliceNet" &&
                $child_type ne "npiNlPseudoNet"} {
                release_netlist $child
                continue
            }
        }
        lappend stack [list $child $module_depth [expr {$stack_depth + 1}] 1]
    }
}

proc ::rscheck_inventory::release_owned_stack {stack} {
    foreach item $stack {
        if {[lindex $item 3]} {
            release_netlist [lindex $item 0]
        }
    }
}

proc ::rscheck_inventory::discover_upstream_modules {start module_depth state_id} {
    variable maximum_object_stack_depth
    set stack [list [list $start $module_depth 0 0]]
    set hits {}
    array set hit_seen {}
    while {[llength $stack] > 0} {
        set index [expr {[llength $stack] - 1}]
        set item [lindex $stack $index]
        set stack [lreplace $stack $index $index]
        set handle [lindex $item 0]
        set current_module_depth [lindex $item 1]
        set stack_depth [lindex $item 2]
        set owned [lindex $item 3]
        if {$handle eq ""} {continue}
        if {$stack_depth > $maximum_object_stack_depth} {
            mark_trace_unresolved $state_id "clock trace exceeded the $maximum_object_stack_depth Netlist traversal stack limit"
            if {$owned} {release_netlist $handle}
            continue
        }
        if {![begin_trace_object $state_id $handle $current_module_depth]} {
            if {$owned} {release_netlist $handle}
            continue
        }

        set type [netlist_string $handle npiNlType]
        set stop 0
        if {$type eq "npiNlInstPort" || $type eq "npiNlPseudoInstPort"} {
            set direction [netlist_string $handle npiNlDirection]
            set instance [owning_instance $handle]
            set module_cell [expr {$instance ne "" &&
                [netlist_string $instance npiNlCellType] eq "npiNlModuleCell"}]
            if {$module_cell && ($direction eq "npiNlOutput" || $direction eq "npiNlInout")} {
                set hit [module_hit_from_instance $instance $state_id]
                if {$hit ne ""} {
                    set hit_key "[lindex $hit 0]\x1f[lindex $hit 1]"
                    if {![info exists hit_seen($hit_key)]} {
                        set hit_seen($hit_key) 1
                        lappend hits $hit
                    }
                }
                set stop 1
            } elseif {$module_cell && $direction ne "npiNlInput"} {
                set port_name [netlist_string $handle npiNlFullName]
                if {$port_name eq ""} {set port_name [netlist_string $handle npiNlName]}
                mark_trace_unresolved $state_id "NPI Netlist module port has unknown direction: $port_name"
            }
            if {!$stop && $instance ne "" && !$module_cell && $direction ne "npiNlInput"} {
                lappend stack [list $instance $current_module_depth [expr {$stack_depth + 1}] 1]
                set instance ""
                set stop 1
            }
            if {$instance ne ""} {release_netlist $instance}
        } elseif {$type eq "npiNlInst" &&
                  [netlist_string $handle npiNlCellType] eq "npiNlModuleCell"} {
            set hit [module_hit_from_instance $handle $state_id]
            if {$hit ne ""} {
                set hit_key "[lindex $hit 0]\x1f[lindex $hit 1]"
                if {![info exists hit_seen($hit_key)]} {
                    set hit_seen($hit_key) 1
                    lappend hits $hit
                }
            }
            set stop 1
        }

        if {!$stop} {
            append_netlist_relation stack npiNlDriver $handle $current_module_depth $stack_depth
            if {$type eq "npiNlDeclNet" || $type eq "npiNlConcatNet" ||
                $type eq "npiNlSliceNet" || $type eq "npiNlPseudoNet"} {
                append_netlist_relation stack npiNlConnectivity $handle $current_module_depth $stack_depth 1
            }
        }
        if {$owned} {release_netlist $handle}
    }
    return [lsort -ascii -index 0 $hits]
}

proc ::rscheck_inventory::netlist_handle_by_name {name type} {
    if {$name eq ""} {return ""}
    if {[catch {set handle [npi_nl_handle_by_name -name $name -type $type]}]} {
        return ""
    }
    return $handle
}

proc ::rscheck_inventory::preferred_netlist_handle_by_name {name type} {
    set handle [netlist_handle_by_name $name $type]
    if {$handle ne ""} {return $handle}
    return [netlist_handle_by_name $name npiNlUndefined]
}

proc ::rscheck_inventory::resolve_trace_start {instance_full_name clock_port port_info} {
    set names {}
    set formal_name [dict get $port_info full_name]
    if {$formal_name ne ""} {lappend names $formal_name}
    if {$instance_full_name ne "" && $clock_port ne ""} {
        set constructed "$instance_full_name.$clock_port"
        if {[lsearch -exact $names $constructed] < 0} {lappend names $constructed}
    }
    foreach name $names {
        set handle [preferred_netlist_handle_by_name $name npiNlInstPort]
        if {$handle ne ""} {return $handle}
    }
    set connection [dict get $port_info connection]
    if {$connection ne ""} {
        return [preferred_netlist_handle_by_name $connection npiNlNet]
    }
    return ""
}

proc ::rscheck_inventory::source_compare {left right} {
    set left_depth [dict get $left depth]
    set right_depth [dict get $right depth]
    if {$left_depth < $right_depth} {return -1}
    if {$left_depth > $right_depth} {return 1}
    foreach field {instance module} {
        set comparison [string compare [dict get $left $field] [dict get $right $field]]
        if {$comparison != 0} {return $comparison}
    }
    return [string compare [dict get $left path] [dict get $right path]]
}

proc ::rscheck_inventory::append_module_hits {hits depth parent_path queue_var state_id max_depth} {
    variable trace_modules
    variable trace_depth_limited
    upvar 1 $queue_var queue
    foreach hit $hits {
        set instance [lindex $hit 0]
        set module [lindex $hit 1]
        set path $parent_path
        lappend path $instance
        set source [dict create instance $instance module $module depth $depth path $path]
        set index [state_index $state_id $instance]
        set keep 1
        if {[info exists trace_modules($index)]} {
            set existing $trace_modules($index)
            set existing_depth [dict get $existing depth]
            if {$existing_depth < $depth ||
                ($existing_depth == $depth &&
                 [string compare [dict get $existing path] $path] <= 0)} {
                set keep 0
            }
        }
        if {!$keep} {continue}
        set trace_modules($index) $source
        if {$depth >= $max_depth} {
            set trace_depth_limited($state_id) 1
        } else {
            lappend queue [list $instance $module $depth $path]
        }
    }
}

proc ::rscheck_inventory::trace_netlist_input_relation {relation instance frontier queue_var state_id max_depth scanned_var classified_var resolved_var unknown_var unnamed_var} {
    upvar 1 $queue_var queue
    upvar 1 $scanned_var scanned
    upvar 1 $classified_var classified
    upvar 1 $resolved_var resolved
    upvar 1 $unknown_var unknown
    upvar 1 $unnamed_var unnamed
    if {[catch {set iterator [npi_nl_iterate -type $relation -refHandle $instance]}] || $iterator eq ""} {
        return
    }
    set current_depth [lindex $frontier 2]
    set current_path [lindex $frontier 3]
    while {1} {
        if {[catch {set port [npi_nl_scan -iterator $iterator]}]} {break}
        if {$port eq ""} {break}
        incr scanned
        set direction [netlist_string $port npiNlDirection]
        set name [netlist_string $port npiNlName]
        if {$direction eq "npiNlInput" || $direction eq "npiNlOutput" || $direction eq "npiNlInout"} {
            if {$name ne ""} {dict set classified $name 1}
        }
        if {$direction ne "npiNlInput"} {
            if {$direction eq "npiNlOutput" || $direction eq "npiNlInout"} {
                if {$name ne ""} {dict set resolved $name 1}
            } elseif {$name eq ""} {
                incr unnamed
            } else {
                dict set unknown $name 1
            }
            release_netlist $port
            continue
        }
        if {$name eq "clk" || $name eq "rst_n"} {
            dict set resolved $name 1
            release_netlist $port
            continue
        }
        set hits [discover_upstream_modules $port $current_depth $state_id]
        if {[llength $hits] > 0 && $name ne ""} {dict set resolved $name 1}
        append_module_hits $hits [expr {$current_depth + 1}] $current_path queue $state_id $max_depth
        release_netlist $port
    }
}

proc ::rscheck_inventory::trace_language_input_ports {frontier resolved queue_var state_id max_depth classified_var} {
    upvar 1 $queue_var queue
    upvar 1 $classified_var classified
    set instance_name [lindex $frontier 0]
    set current_depth [lindex $frontier 2]
    set current_path [lindex $frontier 3]
    if {[catch {set module [npi_handle_by_name -name $instance_name -scope ""]}]} {
        set module ""
    }
    set ports [dict create]
    if {$module ne ""} {
        set ports [collect_ports $module $instance_name $state_id]
        release_language $module
    } elseif {[llength [info commands ::npi_L1::npi_mod_inst_get_port]]} {
        set fallback_ports {}
        if {![catch {::npi_L1::npi_mod_inst_get_port $instance_name fallback_ports}]} {
            foreach port $fallback_ports {
                if {$port eq ""} {continue}
                merge_port ports $port $instance_name $state_id
                release_language $port
            }
        }
    }
    if {[dict size $ports] == 0} {return 0}
    set unknown_count 0
    foreach name [lsort -ascii [dict keys $ports]] {
        if {[dict exists $resolved $name]} {continue}
        set info [dict get $ports $name]
        set direction [dict get $info direction]
        if {$direction eq ""} {
            incr unknown_count
            continue
        }
        dict set classified $name 1
        if {$direction ne "npiInput" || $name eq "clk" || $name eq "rst_n"} {
            continue
        }
        set start [resolve_trace_start $instance_name $name $info]
        if {$start eq ""} {
            mark_trace_unresolved $state_id "NPI could not resolve intermediate input port: $instance_name.$name"
            continue
        }
        set hits [discover_upstream_modules $start $current_depth $state_id]
        release_netlist $start
        append_module_hits $hits [expr {$current_depth + 1}] $current_path queue $state_id $max_depth
    }
    if {$unknown_count != 0} {
        mark_trace_unresolved $state_id "NPI fallback returned $unknown_count intermediate port(s) with unknown direction for module: $instance_name"
    }
    return 1
}

proc ::rscheck_inventory::expand_module_inputs {frontier queue_var state_id max_depth} {
    variable trace_expanded_module_depth
    upvar 1 $queue_var queue
    set instance_name [lindex $frontier 0]
    set current_depth [lindex $frontier 2]
    set state_index_value [state_index $state_id $instance_name]
    if {[info exists trace_expanded_module_depth($state_index_value)] &&
        $trace_expanded_module_depth($state_index_value) <= $current_depth} {
        return
    }
    set trace_expanded_module_depth($state_index_value) $current_depth

    set scanned 0
    set unnamed 0
    set classified [dict create]
    set resolved [dict create]
    set unknown [dict create]
    set instance [preferred_netlist_handle_by_name $instance_name npiNlInst]
    if {$instance ne ""} {
        trace_netlist_input_relation npiNlInstPort $instance $frontier queue $state_id $max_depth scanned classified resolved unknown unnamed
        trace_netlist_input_relation npiNlPseudoInstPort $instance $frontier queue $state_id $max_depth scanned classified resolved unknown unnamed
        release_netlist $instance
    }
    set fallback_classified [dict create]
    set fallback_available [trace_language_input_ports $frontier $resolved queue $state_id $max_depth fallback_classified]
    set unresolved_unknown $unnamed
    foreach name [dict keys $unknown] {
        if {![dict exists $classified $name] && ![dict exists $fallback_classified $name]} {
            incr unresolved_unknown
        }
    }
    if {$unresolved_unknown != 0} {
        mark_trace_unresolved $state_id "NPI Netlist returned $unresolved_unknown intermediate port(s) with unknown direction for module: $instance_name"
    }
    if {!$fallback_available && $scanned == 0} {
        mark_trace_unresolved $state_id "NPI could not enumerate input ports for upstream module: $instance_name"
    }
}

proc ::rscheck_inventory::cleanup_trace_state {state_id} {
    variable trace_unresolved
    variable trace_depth_limited
    variable trace_object_visits
    variable trace_diagnostics
    variable trace_diagnostic_seen
    variable trace_best_object_depth
    variable trace_expanded_module_depth
    variable trace_modules
    foreach array_name {trace_diagnostic_seen trace_best_object_depth trace_expanded_module_depth trace_modules} {
        upvar 0 ::rscheck_inventory::$array_name values
        foreach index [array names values "$state_id\x1e*"] {
            unset values($index)
        }
    }
    catch {unset trace_unresolved($state_id)}
    catch {unset trace_depth_limited($state_id)}
    catch {unset trace_object_visits($state_id)}
    catch {unset trace_diagnostics($state_id)}
}

proc ::rscheck_inventory::trace_clock {instance_full_name clock_port port_info max_depth} {
    variable trace_unresolved
    variable trace_depth_limited
    variable trace_diagnostics
    variable trace_modules
    set state_id [new_trace_state]
    set start [resolve_trace_start $instance_full_name $clock_port $port_info]
    set queue {}
    if {$start eq ""} {
        mark_trace_unresolved $state_id "NPI Netlist could not resolve clock port: $instance_full_name.$clock_port"
    } else {
        set hits [discover_upstream_modules $start 0 $state_id]
        release_netlist $start
        append_module_hits $hits 1 {} queue $state_id $max_depth
        while {[llength $queue] > 0} {
            set frontier [lindex $queue 0]
            set queue [lrange $queue 1 end]
            expand_module_inputs $frontier queue $state_id $max_depth
        }
        set module_count 0
        foreach index [array names trace_modules "$state_id\x1e*"] {incr module_count}
        if {$module_count == 0 && !$trace_unresolved($state_id)} {
            add_trace_diagnostic $state_id "no upstream module output was resolved for clock port: $instance_full_name.$clock_port"
        }
    }
    set modules {}
    foreach index [array names trace_modules "$state_id\x1e*"] {
        lappend modules $trace_modules($index)
    }
    set modules [lsort -command ::rscheck_inventory::source_compare $modules]
    set diagnostics [lsort -ascii $trace_diagnostics($state_id)]
    if {$trace_unresolved($state_id)} {
        set status unresolved
    } elseif {$trace_depth_limited($state_id)} {
        set status depth_limited
    } else {
        set status complete
    }
    set result [dict create clock_port $clock_port max_depth $max_depth \
        status $status modules $modules diagnostics $diagnostics]
    cleanup_trace_state $state_id
    return $result
}

proc ::rscheck_inventory::empty_port_info {} {
    return [dict create connection "" object_type "" full_name "" direction ""]
}

proc ::rscheck_inventory::build_instance {module_handle trace_rules default_clk max_depth} {
    set name [language_string $module_handle npiName]
    set full_name [language_string $module_handle npiFullName]
    set module [language_string $module_handle npiDefName]
    set file [language_string $module_handle npiFile]
    set line [language_integer $module_handle npiLineNo]
    if {![string is integer -strict $line] || $line <= 0} {set line ""}
    set ports [collect_ports $module_handle $full_name]
    set parameters [collect_parameters $module_handle $full_name]
    set has_trace 0
    set clock_port ""
    if {[dict size $trace_rules] == 0} {
        set clock_port $default_clk
        if {[dict exists $ports $clock_port]} {set has_trace 1}
    } elseif {[dict exists $trace_rules $module]} {
        set clock_port [dict get $trace_rules $module]
        set has_trace 1
    }
    set clock_trace ""
    set clk_sources {}
    if {$has_trace} {
        if {[dict exists $ports $clock_port]} {
            set port_info [dict get $ports $clock_port]
        } else {
            set port_info [empty_port_info]
        }
        set clock_trace [trace_clock $full_name $clock_port $port_info $max_depth]
        foreach source [dict get $clock_trace modules] {
            lappend clk_sources [dict create instance [dict get $source instance] module [dict get $source module]]
        }
    }
    return [dict create name $name full_name $full_name module $module file $file line $line \
        ports $ports parameters $parameters clk_sources $clk_sources has_clock_trace $has_trace \
        clock_trace $clock_trace]
}

proc ::rscheck_inventory::instance_compare {left right} {
    set comparison [string compare [dict get $left full_name] [dict get $right full_name]]
    if {$comparison != 0} {return $comparison}
    return [string compare [dict get $left name] [dict get $right name]]
}

proc ::rscheck_inventory::collect_immediate_modules {scope depth visited_var emitted_var instances_var trace_rules default_clk max_depth} {
    variable maximum_scope_depth
    upvar 1 $visited_var visited
    upvar 1 $emitted_var emitted
    upvar 1 $instances_var instances
    if {$scope eq ""} {return}
    if {$depth > $maximum_scope_depth} {
        add_warning "language hierarchy traversal exceeded the depth limit at [language_string $scope npiFullName]"
        return
    }
    set key [language_key $scope]
    if {[info exists visited($key)]} {return}
    set visited($key) 1
    if {[catch {set iterator [npi_iterate -type npiInternalScope -refHandle $scope]}] || $iterator eq ""} {
        return
    }
    while {1} {
        if {[catch {set child [npi_scan -iterator $iterator]}]} {break}
        if {$child eq ""} {break}
        set type [language_string $child npiType]
        if {$type eq "npiModule"} {
            set child_key [language_key $child]
            if {![info exists emitted($child_key)]} {
                set emitted($child_key) 1
                lappend instances [build_instance $child $trace_rules $default_clk $max_depth]
            }
        } elseif {$type eq "npiGenScope"} {
            collect_immediate_modules $child [expr {$depth + 1}] visited emitted instances $trace_rules $default_clk $max_depth
        }
        release_language $child
    }
}

proc ::rscheck_inventory::collect_position {position trace_rules default_clk max_depth} {
    if {[catch {set scope [npi_handle_by_name -name $position -scope ""]}]} {
        set scope ""
    }
    if {$scope eq ""} {
        return [dict create found 0 instances {}]
    }
    set type [language_string $scope npiType]
    if {$type ne "npiModule" && $type ne "npiInterface" &&
        $type ne "npiProgram" && $type ne "npiGenScope"} {
        add_warning "hierarchy position does not resolve to a supported scope: $position ($type)"
        release_language $scope
        return [dict create found 0 instances {}]
    }
    array set visited {}
    array set emitted {}
    set instances {}
    collect_immediate_modules $scope 0 visited emitted instances $trace_rules $default_clk $max_depth
    release_language $scope
    set instances [lsort -command ::rscheck_inventory::instance_compare $instances]
    return [dict create found 1 instances $instances]
}

proc ::rscheck_inventory::json_string_array {values} {
    set raw {}
    foreach value $values {lappend raw [json_string $value]}
    return [json_array_raw $raw]
}

proc ::rscheck_inventory::port_map_json {ports} {
    set pairs {}
    foreach name [lsort -ascii [dict keys $ports]] {
        set info [dict get $ports $name]
        set item [json_object_raw [list \
            connection [json_string [dict get $info connection]] \
            type [json_string [dict get $info object_type]]]]
        lappend pairs $name $item
    }
    return [json_object_raw $pairs]
}

proc ::rscheck_inventory::parameter_map_json {parameters} {
    set pairs {}
    foreach name [lsort -ascii [dict keys $parameters]] {
        set info [dict get $parameters $name]
        if {[lindex $info 0]} {
            set raw [json_string [lindex $info 1]]
        } else {
            set raw null
        }
        lappend pairs $name $raw
    }
    return [json_object_raw $pairs]
}

proc ::rscheck_inventory::source_list_json {sources include_trace_fields} {
    set raw {}
    foreach source $sources {
        set pairs [list \
            instance [json_string [dict get $source instance]] \
            module [json_string [dict get $source module]]]
        if {$include_trace_fields} {
            lappend pairs depth [dict get $source depth]
            lappend pairs path [json_string_array [dict get $source path]]
        }
        lappend raw [json_object_raw $pairs]
    }
    return [json_array_raw $raw]
}

proc ::rscheck_inventory::clock_trace_json {trace} {
    return [json_object_raw [list \
        clock_port [json_string [dict get $trace clock_port]] \
        max_depth [dict get $trace max_depth] \
        excluded_inputs [json_string_array [list clk rst_n]] \
        status [json_string [dict get $trace status]] \
        modules [source_list_json [dict get $trace modules] 1] \
        diagnostics [json_string_array [dict get $trace diagnostics]]]]
}

proc ::rscheck_inventory::instance_json {instance} {
    set line [dict get $instance line]
    if {$line eq ""} {set line_raw null} else {set line_raw $line}
    if {[dict get $instance has_clock_trace]} {
        set trace_raw [clock_trace_json [dict get $instance clock_trace]]
    } else {
        set trace_raw null
    }
    return [json_object_raw [list \
        name [json_string [dict get $instance name]] \
        full_name [json_string [dict get $instance full_name]] \
        module [json_string [dict get $instance module]] \
        file [json_string [dict get $instance file]] \
        line $line_raw \
        ports [port_map_json [dict get $instance ports]] \
        parameters [parameter_map_json [dict get $instance parameters]] \
        clk_sources [source_list_json [dict get $instance clk_sources] 0] \
        clock_trace $trace_raw]]
}

proc ::rscheck_inventory::position_json {position_info} {
    set instances_raw {}
    foreach instance [dict get $position_info instances] {
        lappend instances_raw [instance_json $instance]
    }
    set found [expr {[dict get $position_info found] ? "true" : "false"}]
    return [json_object_raw [list found $found instances [json_array_raw $instances_raw]]]
}

proc ::rscheck_inventory::inventory_json {positions position_results} {
    variable warnings
    set position_pairs {}
    foreach position $positions {
        lappend position_pairs $position [position_json [dict get $position_results $position]]
    }
    set warning_values [lsort -ascii [array names warnings]]
    return [json_object_raw [list \
        schema_version 3 \
        positions [json_object_raw $position_pairs] \
        warnings [json_string_array $warning_values] \
        notices [json_string_array {}]]]
}

proc ::rscheck_inventory::write_inventory_file {path inventory} {
    if {$path eq ""} {return}
    if {[catch {set fp [open $path w]} message]} {
        error "cannot open inventory output file: $path: $message"
    }
    fconfigure $fp -translation lf -encoding utf-8
    if {[catch {puts $fp $inventory} message]} {
        catch {close $fp}
        error "cannot write inventory output file: $path: $message"
    }
    if {[catch {close $fp} message]} {
        error "cannot close inventory output file: $path: $message"
    }
}

proc ::rscheck_inventory::collect {} {
    variable warnings
    catch {array unset warnings}
    array set warnings {}
    set positions_file [env_value KDEBUG_RSCHECK_POSITIONS_FILE ""]
    set trace_rules_file [env_value KDEBUG_RSCHECK_TRACE_RULES_FILE ""]
    set output_file [env_value KDEBUG_RSCHECK_OUTPUT_JSON ""]
    set default_clk [env_value KDEBUG_RSCHECK_CLK_PORT clk]
    set default_rst [env_value KDEBUG_RSCHECK_RST_PORT rst_n]
    set max_depth [parse_trace_depth [env_value KDEBUG_RSCHECK_TRACE_MAX_DEPTH ""]]
    if {$default_clk eq "" || $default_rst eq ""} {
        error "default clock and reset port names must not be empty"
    }
    set positions [read_positions $positions_file]
    set trace_rules [read_trace_rules $trace_rules_file]
    set top_names [query_top_instances]
    if {[llength $top_names] == 0} {
        return [dict create ok 0 code NPI_LOAD \
            message "no top instance is queryable in Verdi elaborated KDB"]
    }
    set results [dict create]
    set instance_count 0
    foreach position $positions {
        set result [collect_position $position $trace_rules $default_clk $max_depth]
        dict set results $position $result
        incr instance_count [llength [dict get $result instances]]
    }
    set inventory [inventory_json $positions $results]
    write_inventory_file $output_file $inventory
    set summary [json_object_raw [list \
        position_count [llength $positions] \
        instance_count $instance_count \
        warning_count [array size warnings] \
        top_count [llength $top_names] \
        top_names [json_string_array $top_names]]]
    return [dict create ok 1 inventory $inventory summary $summary]
}

# Public entry point used by kdebug_npi.tcl.
proc rscheck_inventory_action {} {
    if {[catch {set result [::rscheck_inventory::collect]} message options]} {
        if {[catch {dict get $options -errorinfo} error_info]} {
            set error_info $message
        }
        fail_data RSCHECK_INVENTORY_FAILED "$message\n$error_info"
        return
    }
    if {![dict get $result ok]} {
        fail_data [dict get $result code] [dict get $result message]
        return
    }
    ok_data [list \
        inventory [dict get $result inventory] \
        summary [dict get $result summary]]
}
