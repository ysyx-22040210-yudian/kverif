set here [file dirname [file normalize [info script]]]
source [file join $here .. .. tcl_engine rscheck_inventory.tcl]

proc assert_true {condition message} {
    if {![uplevel 1 [list expr $condition]]} {
        error "assertion failed: $message"
    }
}

proc json_escape {value} {
    return [string map [list "\\" "\\\\" "\"" "\\\"" "\n" "\\n" "\r" "\\r" "\t" "\\t"] $value]
}

proc json_string {value} {return "\"[json_escape $value]\""}

proc json_array_raw {values} {return "\[[join $values ,]\]"}

proc json_object_raw {pairs} {
    set fields {}
    foreach {name value} $pairs {
        lappend fields "[json_string $name]:$value"
    }
    return "\{[join $fields ,]\}"
}

proc ok_data {pairs} {set ::action_response [json_object_raw [list ok true data [json_object_raw $pairs]]]}
proc fail_data {code message} {
    set ::action_response [json_object_raw [list ok false error [json_object_raw [list code [json_string $code] message [json_string $message]]]]]
}

set ::mock_top_enabled 1
set ::mock_iterator_sequence 0
array set ::mock_iterator_values {}
array set ::mock_iterator_index {}

proc mock_iterator {values} {
    incr ::mock_iterator_sequence
    set name "mock_iter_$::mock_iterator_sequence"
    set ::mock_iterator_values($name) $values
    set ::mock_iterator_index($name) 0
    return $name
}

proc npi_iterate {args} {
    set type ""
    set reference ""
    foreach {name value} $args {
        if {$name eq "-type"} {set type $value}
        if {$name eq "-refHandle"} {set reference $value}
    }
    if {$type eq "npiInstance" && $reference eq "" && $::mock_top_enabled} {
        return [mock_iterator [list mock_top]]
    }
    return ""
}

proc npi_scan {args} {
    set iterator [lindex $args 1]
    if {![info exists ::mock_iterator_values($iterator)]} {return ""}
    set index $::mock_iterator_index($iterator)
    set values $::mock_iterator_values($iterator)
    if {$index >= [llength $values]} {return ""}
    set ::mock_iterator_index($iterator) [expr {$index + 1}]
    return [lindex $values $index]
}

proc npi_get_str {args} {
    set property [lindex $args 1]
    set object [lindex $args 3]
    if {$object eq "mock_top" && $property eq "npiFullName"} {return top}
    if {$object eq "mock_top" && $property eq "npiName"} {return top}
    if {$object eq "mock_top" && $property eq "npiType"} {return npiModule}
    return ""
}

proc npi_get {args} {return ""}
proc npi_get_value {args} {
    set object [lindex $args 3]
    if {$object eq "mock_bad_parameter"} {return NPI_GET_VALUE_ERROR_STR}
    return 1
}
proc npi_release_handle {args} {return}
proc npi_handle_by_name {args} {return ""}

array set ::mock_netlist_release_count {}
set ::mock_netlist_lookup_calls {}
proc npi_nl_get_str {args} {
    set property [lindex $args 1]
    set object [lindex $args 3]
    if {$object eq "mock_output_port" && $property eq "npiNlType"} {return npiNlInstPort}
    if {$object eq "mock_output_port" && $property eq "npiNlDirection"} {return npiNlOutput}
    if {$object eq "mock_output_port" && $property eq "npiNlFullName"} {return top.u_src.clk_out}
    if {$object eq "mock_upstream" && $property eq "npiNlType"} {return npiNlInst}
    if {$object eq "mock_upstream" && $property eq "npiNlCellType"} {return npiNlModuleCell}
    if {$object eq "mock_upstream" && $property eq "npiNlFullName"} {return top.u_src}
    if {$object eq "mock_upstream" && $property eq "npiNlDefName"} {return clock_source}
    if {$object eq "mock_clock_formal" && $property eq "npiNlType"} {return npiNlInstPort}
    if {$object eq "mock_clock_formal" && $property eq "npiNlDirection"} {return npiNlInput}
    if {$object eq "mock_clock_formal" && $property eq "npiNlFullName"} {return top.u_rs.clk}
    if {$object eq "mock_clock_formal" && $property eq "npiNlName"} {return clk}
    if {$object eq "mock_collision_instance" && $property eq "npiNlType"} {return npiNlInst}
    if {$object eq "mock_collision_instance" && $property eq "npiNlCellType"} {return npiNlModuleCell}
    if {$object eq "mock_collision_instance" && $property eq "npiNlFullName"} {return top.u_false_crg}
    if {$object eq "mock_collision_instance" && $property eq "npiNlDefName"} {return false_crg}
    if {$object eq "mock_shared_net" && $property eq "npiNlType"} {return npiNlDeclNet}
    if {$object eq "mock_shared_net" && $property eq "npiNlFullName"} {return top.shared_clock}
    return ""
}
proc npi_nl_handle {args} {
    set relation [lindex $args 1]
    set object [lindex $args 3]
    if {$relation eq "npiNlInst" && $object eq "mock_output_port"} {
        return mock_upstream
    }
    return ""
}
proc npi_nl_handle_by_name {args} {
    set name ""
    set type npiNlUndefined
    foreach {key value} $args {
        if {$key eq "-name"} {set name $value}
        if {$key eq "-type"} {set type $value}
    }
    lappend ::mock_netlist_lookup_calls [list $name $type]
    if {$name eq "top.u_rs.clk"} {
        if {$type eq "npiNlInstPort"} {return mock_clock_formal}
        if {$type eq "npiNlUndefined"} {return mock_collision_instance}
    }
    if {$name eq "top.shared_clock"} {
        if {$type eq "npiNlNet"} {return mock_shared_net}
        if {$type eq "npiNlUndefined"} {return mock_collision_instance}
    }
    if {$name eq "top.u_src"} {
        if {$type eq "npiNlInst"} {return mock_upstream}
        if {$type eq "npiNlUndefined"} {return mock_shared_net}
    }
    return ""
}
proc npi_nl_iterate {args} {
    set type ""
    set reference ""
    foreach {key value} $args {
        if {$key eq "-type"} {set type $value}
        if {$key eq "-refHandle"} {set reference $value}
    }
    if {$type eq "npiNlDriver" && $reference eq "mock_clock_formal"} {
        return [mock_iterator [list mock_output_port]]
    }
    return ""
}
proc npi_nl_scan {args} {return [npi_scan {*}$args]}
proc npi_nl_release_handle {args} {
    set object [lindex $args 1]
    if {![info exists ::mock_netlist_release_count($object)]} {
        set ::mock_netlist_release_count($object) 0
    }
    incr ::mock_netlist_release_count($object)
}

proc run_tests {} {
set temp_root [file join [pwd] "rscheck_inventory_tcl_test_[pid]"]
set ::rscheck_inventory_test_temp_root $temp_root
file mkdir $temp_root
set positions_file [file join $temp_root positions.txt]
set rules_file [file join $temp_root rules.tsv]
set output_file [file join $temp_root inventory.json]

set fp [open $positions_file w]
puts $fp " missing.position "
puts $fp "missing.position"
close $fp
set fp [open $rules_file w]
puts $fp "rs_pipe\tclk"
close $fp

set ::env(KDEBUG_RSCHECK_POSITIONS_FILE) $positions_file
set ::env(KDEBUG_RSCHECK_TRACE_RULES_FILE) $rules_file
set ::env(KDEBUG_RSCHECK_OUTPUT_JSON) $output_file
set ::env(KDEBUG_RSCHECK_TRACE_MAX_DEPTH) 16
set ::env(KDEBUG_RSCHECK_CLK_PORT) clk
set ::env(KDEBUG_RSCHECK_RST_PORT) rst_n

assert_true {[::rscheck_inventory::parse_trace_depth 1] == 1} "minimum trace depth"
assert_true {[::rscheck_inventory::parse_trace_depth 256] == 256} "maximum trace depth"
assert_true {[catch {::rscheck_inventory::parse_trace_depth 0}]} "zero trace depth rejected"
assert_true {[catch {::rscheck_inventory::parse_trace_depth 257}]} "oversized trace depth rejected"
assert_true {[::rscheck_inventory::read_positions $positions_file] eq "missing.position"} "positions are trimmed and deduplicated"
assert_true {[::rscheck_inventory::parameter_value mock_parameter] eq "1 1"} "parameter value is retained"
assert_true {[::rscheck_inventory::parameter_value mock_bad_parameter] eq "0 {}"} "NPI value error becomes unresolved"

set state_id [::rscheck_inventory::new_trace_state]
::rscheck_inventory::add_trace_diagnostic $state_id "test diagnostic"
::rscheck_inventory::cleanup_trace_state $state_id
assert_true {![info exists ::rscheck_inventory::trace_unresolved($state_id)]} "trace state is cleaned"

set state_id [::rscheck_inventory::new_trace_state]
set hits [::rscheck_inventory::discover_upstream_modules mock_output_port 0 $state_id]
assert_true {[llength $hits] == 1} "module output is discovered"
assert_true {[lindex [lindex $hits 0] 0] eq "top.u_src"} "module instance is retained"
assert_true {$::mock_netlist_release_count(mock_upstream) == 1} "owned module handle is released exactly once"
::rscheck_inventory::cleanup_trace_state $state_id

set collision_port [dict create connection top.shared_clock object_type npiNet \
    full_name top.u_rs.clk direction npiInput]
set trace [::rscheck_inventory::trace_clock top.u_rs clk $collision_port 1]
set traced_modules [dict get $trace modules]
assert_true {[llength $traced_modules] == 1} "typed formal lookup yields one true driver"
assert_true {[dict get [lindex $traced_modules 0] instance] eq "top.u_src"} "same-named instance cannot replace the formal port"
assert_true {[dict get [lindex $traced_modules 0] module] eq "clock_source"} "collision cannot create a false CRG source"
assert_true {[lsearch -exact $::mock_netlist_lookup_calls [list top.u_rs.clk npiNlInstPort]] >= 0} "formal lookup requests npiNlInstPort"

set connection_only [::rscheck_inventory::empty_port_info]
dict set connection_only connection top.shared_clock
set connection_handle [::rscheck_inventory::resolve_trace_start "" "" $connection_only]
assert_true {$connection_handle eq "mock_shared_net"} "connection lookup prefers the net over a same-named instance"
::rscheck_inventory::release_netlist $connection_handle

set module_handle [::rscheck_inventory::preferred_netlist_handle_by_name top.u_src npiNlInst]
assert_true {$module_handle eq "mock_upstream"} "module lookup prefers the instance over a same-named net"
::rscheck_inventory::release_netlist $module_handle

set rules [::rscheck_inventory::read_trace_rules $rules_file]
assert_true {[dict get $rules rs_pipe] eq "clk"} "trace rule parsed"

set result [::rscheck_inventory::collect]
assert_true {[dict get $result ok]} "inventory collection succeeds with a queryable top"
set inventory [dict get $result inventory]
assert_true {[string first {"schema_version":3} $inventory] >= 0} "inventory schema is v3"
assert_true {[string first {"missing.position":{"found":false,"instances":[]}} $inventory] >= 0} "missing position is represented"
assert_true {[string first {"warnings":[]} $inventory] >= 0} "warnings is an array"
assert_true {[string first {"notices":[]} $inventory] >= 0} "notices is an array"
set fp [open $output_file r]
set written [string trim [read $fp]]
close $fp
assert_true {$written eq $inventory} "optional output contains the same bare inventory"

set ::action_response ""
rscheck_inventory_action
set inventory_needle "\"inventory\":\{\"schema_version\":3"
assert_true {[string first $inventory_needle $::action_response] >= 0} "action response contains data.inventory"
assert_true {[string first {"top_count":1} $::action_response] >= 0} "action summary contains top_count"

set ::mock_top_enabled 0
set failed [::rscheck_inventory::collect]
assert_true {![dict get $failed ok]} "zero top is a hard failure"
assert_true {[dict get $failed code] eq "NPI_LOAD"} "zero top uses NPI_LOAD"

set malformed [file join $temp_root malformed.tsv]
set fp [open $malformed w]
puts $fp "module without tab"
close $fp
assert_true {[catch {::rscheck_inventory::read_trace_rules $malformed}]} "malformed trace rule rejected"

set l1_dir [file join $temp_root mock_l1]
file mkdir $l1_dir
set fp [open [file join $l1_dir npi_L1.tcl] w]
close $fp
set child_script [file join $temp_root response_encoding_child.tcl]
set fp [open $child_script w]
puts $fp {encoding system iso8859-1}
puts $fp {proc debExit {} {return}}
puts $fp [list source [file join $::here .. .. tcl_engine kdebug_npi.tcl]]
puts $fp {set unicode_text [format %c%c 20013 25991]}
puts $fp {write_response_raw [json_object [list message $unicode_text]]}
close $fp
set response_file [file join $temp_root unicode_response.json]
set unicode_text [format %c%c 20013 25991]
set saved_env [dict create]
foreach name {NPIL1_PATH KDEBUG_TCL_ACTION KDEBUG_TCL_RESPONSE_JSON} {
    if {[info exists ::env($name)]} {dict set saved_env $name $::env($name)}
}
set ::env(NPIL1_PATH) $l1_dir
set ::env(KDEBUG_TCL_ACTION) encoding_probe
set ::env(KDEBUG_TCL_RESPONSE_JSON) $response_file
exec [info nameofexecutable] $child_script
foreach name {NPIL1_PATH KDEBUG_TCL_ACTION KDEBUG_TCL_RESPONSE_JSON} {
    catch {unset ::env($name)}
}
dict for {name value} $saved_env {set ::env($name) $value}
set fp [open $response_file rb]
set response_bytes [read $fp]
close $fp
set response_text [encoding convertfrom utf-8 $response_bytes]
assert_true {[string first $unicode_text $response_text] >= 0} "response JSON preserves non-ASCII text as UTF-8"
assert_true {[string first "\r" $response_text] < 0} "response JSON uses LF translation"
assert_true {[string index $response_text end] eq "\n"} "response JSON ends with one LF"

file delete -force $temp_root
unset ::rscheck_inventory_test_temp_root
puts "rscheck inventory Tcl tests: PASS"
}

set test_status [catch {run_tests} test_message test_options]
if {[info exists ::rscheck_inventory_test_temp_root]} {
    catch {file delete -force $::rscheck_inventory_test_temp_root}
    unset ::rscheck_inventory_test_temp_root
}
if {$test_status} {
    puts stderr $test_message
    if {![catch {dict get $test_options -errorinfo} test_error_info]} {
        puts stderr $test_error_info
    }
    exit 1
}
