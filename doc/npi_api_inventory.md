# NPI O-2018.09-SP2 API 逐项覆盖清单

> 本文件由 `kdebug/tools/generate_npi_api_inventory.py` 从手册 outline 生成。
> 来源：`VC_APPS_NPI.pdf`。页码为手册页码。
> 重建：`python kdebug/tools/generate_npi_api_inventory.py --pdf <VC_APPS_NPI.pdf> --output doc/npi_api_inventory.md`。

## 统计口径

- API 目录条目：**759** 条。
- 不同标题：**752** 个。
- 功能域：**28** 个（13 个 Model 域、15 个 Library 域）。
- 同名 API 在手册中可能因重载或章节重复出现；本表保留每个目录条目以便按页追溯。
- `完整覆盖` 表示公共命令可完成同一用户任务，不表示暴露原始 C/C++ ABI。
- `内部覆盖` 表示 handle 生命周期由一次性 Tcl action 自动管理，不提供无效的跨进程 handle。

| 判定 | API 条目数 |
| --- | ---: |
| 完整覆盖 | 119 |
| 部分覆盖 | 348 |
| 等价覆盖 | 27 |
| 内部覆盖 | 4 |
| 许可证阻塞 | 37 |
| 未开放 | 224 |

## 功能域汇总

| 类别 | 功能域 | API 条目 | 完整 | 部分 | 等价/内部 | 许可证阻塞 | 未开放 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NPI Model | Required Models | 3 | 0 | 0 | 3 | 0 | 0 |
| NPI Model | Language Model | 14 | 5 | 4 | 2 | 0 | 3 |
| NPI Model | Netlist Model | 14 | 4 | 2 | 2 | 0 | 6 |
| NPI Model | Text Model | 22 | 13 | 2 | 0 | 0 | 7 |
| NPI Model | Design Manipulation (DM) Model | 133 | 0 | 4 | 0 | 0 | 129 |
| NPI Model | FSDB Model | 49 | 0 | 49 | 0 | 0 | 0 |
| NPI Model | FSDB Model for Transaction | 42 | 0 | 0 | 0 | 0 | 42 |
| NPI Model | NPI FSDB Transaction Writer Model | 22 | 0 | 22 | 0 | 0 | 0 |
| NPI Model | NPI FSDB Writer Model | 23 | 0 | 23 | 0 | 0 | 0 |
| NPI Model | NPI Coverage Model | 19 | 17 | 0 | 0 | 0 | 2 |
| NPI Model | NPI VCS Model | 8 | 0 | 8 | 0 | 0 | 0 |
| NPI Model | NPI Power Model | 10 | 0 | 0 | 0 | 10 | 0 |
| NPI Model | NPI CRDB Model | 18 | 0 | 18 | 0 | 0 | 0 |
| NPI Library | Connection | 28 | 0 | 28 | 0 | 0 | 0 |
| NPI Library | Find | 12 | 4 | 0 | 0 | 0 | 8 |
| NPI Library | VANL Library | 27 | 0 | 0 | 0 | 0 | 27 |
| NPI Library | FSDB Library | 27 | 0 | 27 | 0 | 0 | 0 |
| NPI Library | Power Library | 27 | 0 | 0 | 0 | 27 | 0 |
| NPI Library | FSDB Transaction Writer | 21 | 0 | 21 | 0 | 0 | 0 |
| NPI Library | Hierarchy Tree | 20 | 0 | 20 | 0 | 0 | 0 |
| NPI Library | List | 7 | 0 | 7 | 0 | 0 | 0 |
| NPI Library | Component | 33 | 0 | 33 | 0 | 0 | 0 |
| NPI Library | Miscellaneous | 39 | 0 | 39 | 0 | 0 | 0 |
| NPI Library | Module | 32 | 32 | 0 | 0 | 0 | 0 |
| NPI Library | Netlist Library | 12 | 0 | 12 | 0 | 0 | 0 |
| NPI Library | Signal | 57 | 44 | 13 | 0 | 0 | 0 |
| NPI Library | Utilities | 24 | 0 | 0 | 24 | 0 | 0 |
| NPI Library | CRDB Library | 16 | 0 | 16 | 0 | 0 | 0 |

## 逐 API 清单

### NPI Model: Required Models

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 302 | `npi_end` | 等价覆盖 | `KDebug Verdi wrapper` | 每次 action 自动初始化、加载目标并关闭 NPI |
| 302 | `npi_init` | 等价覆盖 | `KDebug Verdi wrapper` | 每次 action 自动初始化、加载目标并关闭 NPI |
| 306 | `npi_load_design` | 等价覆盖 | `KDebug Verdi wrapper` | 每次 action 自动初始化、加载目标并关闭 NPI |

### NPI Model: Language Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 308 | `npi_compare_objects` | 未开放 | `-` | 尚无对应公共 action |
| 315 | `npi_get` | 部分覆盖 | `language.resolve/module.inspect` | 返回固定安全属性集，不接受任意 property 注入 |
| 319 | `npi_get_str` | 部分覆盖 | `language.resolve/module.inspect` | 返回固定安全属性集，不接受任意 property 注入 |
| 322 | `npi_get_value` | 完整覆盖 | `language.value/module.objects` | 读取 elaborated 参数或常量值 |
| 334 | `npi_handle` | 完整覆盖 | `language.relate` | 按受控 npi* 一对一关系取对象 |
| 337 | `npi_handle_by_index` | 部分覆盖 | `language.resolve` | 可解析带 select 的完整名，未单列 handle 索引 action |
| 342 | `npi_handle_by_name` | 完整覆盖 | `language.resolve` | 按完整名和可选 scope 解析对象 |
| 345 | `npi_handle_by_range` | 部分覆盖 | `language.resolve` | 可解析带 select 的完整名，未单列 handle 索引 action |
| 351 | `npi_iterate` | 完整覆盖 | `language.iterate` | 按受控 npi* object type 遍历 |
| 355 | `npi_objects_overlap` | 未开放 | `-` | 尚无对应公共 action |
| 364 | `npi_release_all_handles` | 内部覆盖 | `所有 Tcl action` | action 内释放 handle，handle 不跨进程泄漏 |
| 367 | `npi_release_handle` | 内部覆盖 | `所有 Tcl action` | action 内释放 handle，handle 不跨进程泄漏 |
| 371 | `npi_scan` | 完整覆盖 | `language.iterate` | 按受控 npi* object type 遍历 |
| 374 | `npi_set_permanent_handle` | 未开放 | `-` | 尚无对应公共 action |

### NPI Model: Netlist Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 378 | `npi_nl_cell_handle_by_name` | 完整覆盖 | `netlist.resolve` | 按名称和可选 npiNl* 类型解析 |
| 380 | `npi_nl_get` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 返回固定网表属性集 |
| 384 | `npi_nl_get_str` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 返回固定网表属性集 |
| 388 | `npi_nl_handle` | 未开放 | `-` | index/range/table 或通用连通关系尚未单列 |
| 391 | `npi_nl_handle_by_index` | 未开放 | `-` | index/range/table 或通用连通关系尚未单列 |
| 395 | `npi_nl_handle_by_name` | 完整覆盖 | `netlist.resolve` | 按名称和可选 npiNl* 类型解析 |
| 401 | `npi_nl_handle_by_range` | 未开放 | `-` | index/range/table 或通用连通关系尚未单列 |
| 405 | `npi_nl_iterate` | 完整覆盖 | `netlist.iterate` | 按受控 npiNl* 类型遍历 |
| 409 | `npi_nl_iterate_with_range` | 未开放 | `-` | index/range/table 或通用连通关系尚未单列 |
| 414 | `npi_nl_release_all_handles` | 内部覆盖 | `netlist.*` | action 内管理 handle 生命周期 |
| 417 | `npi_nl_release_handle` | 内部覆盖 | `netlist.*` | action 内管理 handle 生命周期 |
| 420 | `npi_nl_scan` | 完整覆盖 | `netlist.iterate` | 按受控 npiNl* 类型遍历 |
| 424 | `npi_nl_set_permanent_handle` | 未开放 | `-` | index/range/table 或通用连通关系尚未单列 |
| 428 | `npi_nl_table_lookup` | 未开放 | `-` | index/range/table 或通用连通关系尚未单列 |

### NPI Model: Text Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 433 | `npi_text_delete_line` | 未开放 | `-` | include/macro 展开或其他文本修改尚未开放 |
| 435 | `npi_text_delete_word` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 438 | `npi_text_expand_include` | 未开放 | `-` | include/macro 展开或其他文本修改尚未开放 |
| 441 | `npi_text_expand_macro` | 未开放 | `-` | include/macro 展开或其他文本修改尚未开放 |
| 444 | `npi_text_file_by_include_word` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 447 | `npi_text_file_by_module_name` | 未开放 | `-` | include/macro 展开或其他文本修改尚未开放 |
| 451 | `npi_text_file_by_name` | 完整覆盖 | `text.line` | 文件、行及上下文读取 |
| 453 | `npi_text_handle` | 未开放 | `-` | include/macro 展开或其他文本修改尚未开放 |
| 456 | `npi_text_insert_line_after` | 未开放 | `-` | include/macro 展开或其他文本修改尚未开放 |
| 458 | `npi_text_insert_line_before` | 未开放 | `-` | include/macro 展开或其他文本修改尚未开放 |
| 461 | `npi_text_insert_word_after` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 464 | `npi_text_insert_word_before` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 467 | `npi_text_iter_next` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 470 | `npi_text_iter_start` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 472 | `npi_text_iter_stop` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 474 | `npi_text_line_by_number` | 完整覆盖 | `text.line` | 文件、行及上下文读取 |
| 477 | `npi_text_next_line` | 完整覆盖 | `text.line` | 文件、行及上下文读取 |
| 481 | `npi_text_prev_line` | 完整覆盖 | `text.line` | 文件、行及上下文读取 |
| 485 | `npi_text_property` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 488 | `npi_text_property_str` | 完整覆盖 | `text.words` | word/TWA 属性和遍历 |
| 492 | `npi_text_replace_line` | 部分覆盖 | `text.replace_line` | 仅开放 copy-on-write 行替换 |
| 495 | `npi_text_replace_word` | 部分覆盖 | `text.replace_line` | 仅开放 copy-on-write 行替换 |

### NPI Model: Design Manipulation (DM) Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 498 | `npi_dm_add_enum_member` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 499 | `npi_dm_add_enum_typespec` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 502 | `npi_dm_add_for_component` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 510 | `npi_dm_add_gen_var` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 513 | `npi_dm_add_generate_construct` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 517 | `npi_dm_add_generate_construct_before` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 521 | `npi_dm_add_instance` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 524 | `npi_dm_add_interface_port` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 527 | `npi_dm_add_modport` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 529 | `npi_dm_add_mpport` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 533 | `npi_dm_add_net` | 部分覆盖 | `dm.add_net/dm.clone_module` | 仅开放受控 net 添加和 module 克隆写出 |
| 537 | `npi_dm_add_parameter` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 540 | `npi_dm_add_port` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 543 | `npi_dm_add_process` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 547 | `npi_dm_add_simple_typespec` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 551 | `npi_dm_add_statement` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 555 | `npi_dm_add_statement_before` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 559 | `npi_dm_add_struct_typespec` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 563 | `npi_dm_add_su_member` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 565 | `npi_dm_add_type_parameter` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 568 | `npi_dm_add_union_typespec` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 572 | `npi_dm_add_var` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 575 | `npi_dm_assign_parameter` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 578 | `npi_dm_assign_type_parameter` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 581 | `npi_dm_change_always_type` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 584 | `npi_dm_change_assign_operator` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 586 | `npi_dm_change_blocking` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 589 | `npi_dm_change_case_type` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 592 | `npi_dm_change_data_type` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 594 | `npi_dm_change_net_type` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 596 | `npi_dm_change_signing` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 599 | `npi_dm_change_typespec` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 601 | `npi_dm_clone_module` | 部分覆盖 | `dm.add_net/dm.clone_module` | 仅开放受控 net 添加和 module 克隆写出 |
| 606 | `npi_dm_create_always` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 610 | `npi_dm_create_argument_instance` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 611 | `npi_dm_create_assignment` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 617 | `npi_dm_create_assign_stmt` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 620 | `npi_dm_create_begin` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 622 | `npi_dm_create_break` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 625 | `npi_dm_create_case` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 629 | `npi_dm_create_case_item` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 632 | `npi_dm_create_constant` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 634 | `npi_dm_create_continue` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 637 | `npi_dm_create_db` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 639 | `npi_dm_create_deassign` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 642 | `npi_dm_create_delay_control` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 645 | `npi_dm_create_disable` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 647 | `npi_dm_create_do_while` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 650 | `npi_dm_create_event_control` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 653 | `npi_dm_create_event_stmt` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 656 | `npi_dm_create_for` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 664 | `npi_dm_create_force` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 667 | `npi_dm_create_forever` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 669 | `npi_dm_create_fork` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 671 | `npi_dm_create_function_call` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 679 | `npi_dm_create_gen_block` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 682 | `npi_dm_create_gen_case` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 685 | `npi_dm_create_gen_case_item` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 689 | `npi_dm_create_gen_for` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 693 | `npi_dm_create_gen_if` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 696 | `npi_dm_create_gen_if_else` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 699 | `npi_dm_create_hier_ref` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 702 | `npi_dm_create_if` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 705 | `npi_dm_create_if_else` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 708 | `npi_dm_create_initial` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 710 | `npi_dm_create_interface` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 713 | `npi_dm_create_module` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 715 | `npi_dm_create_named_begin` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 717 | `npi_dm_create_named_fork` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 719 | `npi_dm_create_npiDmBasicDataType` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 720 | `npi_dm_create_npiDmHandleArray` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 721 | `npi_dm_create_null_stmt` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 723 | `npi_dm_create_operation` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 732 | `npi_dm_create_package` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 734 | `npi_dm_create_range` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 736 | `npi_dm_create_ref` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 737 | `npi_dm_create_release` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 740 | `npi_dm_create_repeat` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 743 | `npi_dm_create_repeat_control` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 746 | `npi_dm_create_return_stmt` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 748 | `npi_dm_create_system_function_call` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 751 | `npi_dm_create_system_task_call` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 755 | `npi_dm_create_task_call` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 763 | `npi_dm_create_wait` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 766 | `npi_dm_create_while` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 769 | `npi_dm_delete_assign_connection` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 771 | `npi_dm_delete_bind` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 774 | `npi_dm_delete_db` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 777 | `npi_dm_delete_generate_construct` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 780 | `npi_dm_delete_instance` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 782 | `npi_dm_delete_npiDmBasicDataType` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 783 | `npi_dm_delete_npiDmHandleArray` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 783 | `npi_dm_delete_parameter` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 785 | `npi_dm_delete_port` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 788 | `npi_dm_delete_port_connection` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 790 | `npi_dm_delete_process` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 794 | `npi_dm_delete_session` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 796 | `npi_dm_delete_signal` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 798 | `npi_dm_delete_statement` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 802 | `npi_dm_get_master_db` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 804 | `npi_dm_get_value` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 810 | `npi_dm_handle` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 812 | `npi_dm_handle_by_name` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 814 | `npi_dm_interface_by_name` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 816 | `npi_dm_iter_created_object` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 818 | `npi_dm_iter_next` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 819 | `npi_dm_iter_size` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 821 | `npi_dm_iter_start` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 823 | `npi_dm_iter_stop` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 824 | `npi_dm_load_session` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 826 | `npi_dm_make_assign_connection` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 828 | `npi_dm_make_port_connection` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 831 | `npi_dm_modify_hierarchy` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 835 | `npi_dm_module_by_name` | 部分覆盖 | `dm.add_net/dm.clone_module` | 仅开放受控 net 添加和 module 克隆写出 |
| 836 | `npi_dm_move_instance` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 839 | `npi_dm_package_by_name` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 841 | `npi_dm_param_instance` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 843 | `npi_dm_vh_package_by_name` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 845 | `npi_dm_entity_by_name` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 846 | `npi_dm_architecture_by_name` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 848 | `npi_dm_port_by_name` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 850 | `npi_dm_port_instance` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 852 | `npi_dm_property` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 854 | `npi_dm_property_str` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 857 | `npi_dm_rename_object` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 860 | `npi_dm_replace_expression` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 865 | `npi_dm_replace_module` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 868 | `npi_dm_save_session` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 870 | `npi_dm_set_master_db` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 873 | `npi_dm_sync_format` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 876 | `npi_dm_write_data_mode` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |
| 881 | `npi_dm_write_text_mode` | 部分覆盖 | `dm.add_net/dm.clone_module` | 仅开放受控 net 添加和 module 克隆写出 |
| 883 | `npi_dm_decompile` | 未开放 | `-` | 通用 DM AST 创建、修改和删除未开放 |

### NPI Model: FSDB Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 886 | `npi_fsdb_add_to_sig_list` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 888 | `npi_fsdb_close` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 890 | `npi_fsdb_create_ft` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 893 | `npi_fsdb_release_ft` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 897 | `npi_fsdb_ft_time` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 900 | `npi_fsdb_ft_value` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 904 | `npi_fsdb_create_vct` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 907 | `npi_fsdb_file_property` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 911 | `npi_fsdb_file_property_str` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 913 | `npi_fsdb_goto_first` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 916 | `npi_fsdb_goto_next` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 920 | `npi_fsdb_goto_prev` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 923 | `npi_fsdb_goto_time` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 926 | `npi_fsdb_iter_child_scope` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 928 | `npi_fsdb_iter_member` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 931 | `npi_fsdb_iter_scope_next` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 933 | `npi_fsdb_iter_scope_stop` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 935 | `npi_fsdb_iter_sig` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 937 | `npi_fsdb_iter_sig_next` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 940 | `npi_fsdb_iter_sig_stop` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 943 | `npi_fsdb_iter_top_scope` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 945 | `npi_fsdb_iter_top_sig` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 947 | `npi_fsdb_load_vc_by_range` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 950 | `npi_fsdb_max_time` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 952 | `npi_fsdb_min_time` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 954 | `npi_fsdb_open` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 955 | `npi_fsdb_parent_scope` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 958 | `npi_fsdb_parent_sig` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 960 | `npi_fsdb_release_vct` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 962 | `npi_fsdb_reset_sig_list` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 965 | `npi_fsdb_scope_by_name` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 967 | `npi_fsdb_scope_file` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 969 | `npi_fsdb_scope_property_str` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 972 | `npi_fsdb_sig_by_name` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 975 | `npi_fsdb_sig_file` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 977 | `npi_fsdb_sig_property` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 980 | `npi_fsdb_sig_property_str` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 983 | `npi_fsdb_sig_scope` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 985 | `npi_fsdb_unload_vc` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 988 | `npi_fsdb_update` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 990 | `npi_fsdb_vct_port_value` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 994 | `NPI FSDB Time-Based VC Iterator` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 1000 | `npi_fsdb_vct_seq_num` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 1003 | `npi_fsdb_vct_time` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 1006 | `npi_fsdb_vct_duration` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 1009 | `npi_fsdb_vct_value` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 1028 | `npi_fsdb_vct_value_format` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 1034 | `npi_waveform_open` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |
| 1036 | `npi_waveform_close` | 部分覆盖 | `signal.info/scope.list/value.at/value.batch_at/signal.scan` | 常用 signal FSDB 查询已覆盖；高级 iterator/member API 未逐项开放 |

### NPI Model: FSDB Model for Transaction

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 1039 | `npi_fsdb_add_to_stream_list` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1042 | `npi_fsdb_attr_property` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1046 | `npi_fsdb_attr_property_str` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1049 | `npi_fsdb_create_trt` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1053 | `npi_fsdb_create_trt_by_id` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1057 | `npi_fsdb_goto_first` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1061 | `npi_fsdb_goto_next` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1064 | `npi_fsdb_goto_prev` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1067 | `npi_fsdb_goto_time` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1070 | `npi_fsdb_iter_related_trt` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1075 | `npi_fsdb_iter_relation` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1079 | `npi_fsdb_iter_relation_next` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1083 | `npi_fsdb_iter_relation_stop` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1088 | `npi_fsdb_iter_stream` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1091 | `npi_fsdb_iter_stream_next` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1095 | `npi_fsdb_iter_stream_stop` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1098 | `npi_fsdb_iter_top_tr_scope` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1101 | `npi_fsdb_iter_trt_next` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1106 | `npi_fsdb_iter_trt_stop` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1110 | `npi_fsdb_load_trans` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1113 | `npi_fsdb_relation_property_str` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1118 | `npi_fsdb_release_trt` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1121 | `npi_fsdb_reset_stream_list` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1124 | `npi_fsdb_scope_attr` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1129 | `npi_fsdb_scope_attr_count` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1134 | `npi_fsdb_scope_attr_value` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1139 | `npi_fsdb_stream_attr` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1145 | `npi_fsdb_stream_attr_count` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1150 | `npi_fsdb_stream_attr_value` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1155 | `npi_fsdb_stream_by_name` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1160 | `npi_fsdb_stream_property_str` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1163 | `npi_fsdb_stream_scope` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1165 | `npi_fsdb_tr_scope_by_name` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1169 | `npi_fsdb_trt_attr` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1173 | `npi_fsdb_trt_attr_count` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1178 | `npi_fsdb_trt_attr_value` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1186 | `npi_fsdb_trt_expected_attr` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1190 | `npi_fsdb_trt_id` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1195 | `npi_fsdb_trt_name` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1199 | `npi_fsdb_trt_stream` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1203 | `npi_fsdb_trt_time` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |
| 1206 | `npi_fsdb_unload_trans` | 未开放 | `-` | 当前只提供 transaction writer，不提供 transaction FSDB reader |

### NPI Model: NPI FSDB Transaction Writer Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 1210 | `npi_fsdbw_open` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1212 | `npi_fsdbw_close` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1214 | `npi_fsdbw_flush` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1219 | `npi_fsdbw_incr_time` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1223 | `npi_fsdbw_get_time` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1225 | `npi_fsdbw_file_property_str` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1227 | `npi_fsdbw_scope_add_attr` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1231 | `npi_fsdbw_stream_begin` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1235 | `npi_fsdbw_stream_end` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1240 | `npi_fsdbw_stream_property_str` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1242 | `npi_fsdbw_define_attr` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1247 | `npi_fsdbw_stream_add_attr` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1251 | `npi_fsdbw_trans_begin` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1260 | `npi_fsdbw_set_label` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1265 | `npi_fsdbw_add_tag` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1268 | `npi_fsdbw_trans_end` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1272 | `npi_fsdbw_trans_add_bit_vector_attr (with expected value)` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1273 | `npi_fsdbw_trans_add_bit_vector_attr (with no expected value)` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1274 | `npi_fsdbw_trans_add_attr (with expected attribute)` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1279 | `npi_fsdbw_trans_add_attr (without expected attribute)` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1284 | `npi_fsdbw_add_relation` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |
| 1288 | `npi_fsdbw_add_relation (string type relation name)` | 部分覆盖 | `transaction.writer.create` | 文件、stream、transaction、tag 和 relation 已覆盖；attribute schema 仍有限 |

### NPI Model: NPI FSDB Writer Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 1295 | `npi_fsdbw_create` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1297 | `npi_fsdbw_close` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1300 | `npiFsdbwFileObj::flush()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1301 | `npiFsdbwFileObj::get_time()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1303 | `npiFsdbwFileObj::begin_hierachy_creation` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1305 | `npiFsdbwFileObj::end_hierachy_creation` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1307 | `npiFsdbwFileObj::incr_time` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1310 | `npiFsdbwFileObj::create_scope` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1312 | `npiFsdbwFileObj::up_scope()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1315 | `npiFsdbwFileObj::create_sig` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1320 | `npiFsdbwFileObj::create_eq_sig` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1326 | `npiFsdbwFileObj::get_dt` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1331 | `npiFsdbwFileObj::create_group_dt` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1335 | `npiFsdbwFileObj::create_array_dt` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1340 | `npiFsdbwFileObj::get_leaf_count` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1343 | `npiFsdbwFileObj::get_scope_name()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1346 | `npiFsdbwFileObj::get_scope_full_name()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1349 | `npiFsdbwFileObj::get_scope_depth()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1352 | `npiFsdbwSigObj::add_value` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1358 | `npiFsdbwGroupObj::add()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1362 | `npiFsdbwGroupObj::get_size()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1364 | `npiFsdbwGroupObj::clear()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |
| 1366 | `npiFsdbwSigObj::get_name()` | 部分覆盖 | `fsdb.writer.create_scope` | 文件与 scope 层次已覆盖；signal/value change 尚未开放 |

### NPI Model: NPI Coverage Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 1368 | `npi_cov_close` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1369 | `npi_cov_get` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1371 | `npi_cov_get_str` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1372 | `npi_cov_handle` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1373 | `npi_cov_handle_by_name` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1375 | `npi_cov_has_status` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1377 | `npi_cov_iter_next` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1378 | `npi_cov_iter_start` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1379 | `npi_cov_iter_stop` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1380 | `npi_cov_load_exclude_file` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1382 | `npi_cov_merge_test` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1383 | `npi_cov_open` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1384 | `npi_cov_save_exclude_file` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1386 | `npi_cov_save_test` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1387 | `npi_cov_set` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1391 | `npi_cov_set_status` | 未开放 | `-` | KCov 保持只读分析，不修改 exclusion/status |
| 1392 | `npi_cov_test_by_name` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |
| 1394 | `npi_cov_unload_exclusion` | 未开放 | `-` | KCov 保持只读分析，不修改 exclusion/status |
| 1395 | `npi_cov_unload_test` | 完整覆盖 | `KCov actions` | VDB、test、metric、object、bin 和状态查询由 Tcl NPI 完成 |

### NPI Model: NPI VCS Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 1397 | `npi_vcs_open` | 部分覆盖 | `vcs.summary` | 打开真实 VCS DB 并返回固定编译/设计/仿真统计 |
| 1398 | `npi_vcs_close` | 部分覆盖 | `vcs.summary` | 打开真实 VCS DB 并返回固定编译/设计/仿真统计 |
| 1399 | `npi_vcs_handle` | 部分覆盖 | `vcs.summary` | 打开真实 VCS DB 并返回固定编译/设计/仿真统计 |
| 1400 | `npi_vcs_iterate` | 部分覆盖 | `vcs.summary` | 打开真实 VCS DB 并返回固定编译/设计/仿真统计 |
| 1402 | `npi_vcs_scan` | 部分覆盖 | `vcs.summary` | 打开真实 VCS DB 并返回固定编译/设计/仿真统计 |
| 1403 | `npi_vcs_get` | 部分覆盖 | `vcs.summary` | 打开真实 VCS DB 并返回固定编译/设计/仿真统计 |
| 1405 | `npi_vcs_get_str` | 部分覆盖 | `vcs.summary` | 打开真实 VCS DB 并返回固定编译/设计/仿真统计 |
| 1406 | `npi_vcs_get_value` | 部分覆盖 | `vcs.summary` | 打开真实 VCS DB 并返回固定编译/设计/仿真统计 |

### NPI Model: NPI Power Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 1409 | `npi_pw_design_top` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1410 | `npi_pw_get_domain_crossing_pd` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1420 | `npi_pw_handle` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1421 | `npi_pw_handle_by_name` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1422 | `npi_pw_iter_next` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1424 | `npi_pw_iter_start` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1425 | `npi_pw_iter_stop` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1426 | `npi_pw_power_domain_by_name` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1427 | `npi_pw_property` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |
| 1428 | `npi_pw_property_str` | 许可证阻塞 | `power.resolve/power.list` | Tcl action 已实现；当前 VM 缺少 PowerAwareAnalysis license |

### NPI Model: NPI CRDB Model

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 1430 | `npi_crdb_clone_handle` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1431 | `npi_crdb_release_handle` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1432 | `npi_crdb_open` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1433 | `npi_crdb_close` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1434 | `npi_crdb_save_as` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1435 | `npi_crdb_handle` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1436 | `npi_crdb_iter_start` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1438 | `npi_crdb_iter_next` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1439 | `npi_crdb_iter_stop` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1440 | `npi_crdb_vol_iter_start` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1442 | `npi_crdb_vol_iter_next` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1443 | `npi_crdb_vol_iter_stop` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1444 | `npi_crdb_handle_by_name` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1446 | `npi_crdb_get` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1447 | `npi_crdb_get_str` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1448 | `npi_crdb_set_correlation` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1450 | `npi_crdb_unset_correlation` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |
| 1452 | `npi_crdb_is_correlated` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 对象与 correlation 读取已覆盖；mutation/clone/save-as 未开放 |

### NPI Library: Connection

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 1964 | `npi_inst_port_2_high_conn_sig` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1967 | `npi_inst_port_2_high_conn_sig_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1969 | `npi_inst_port_2_low_conn_sig` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1972 | `npi_inst_port_2_low_conn_sig_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1974 | `npi_nl_sig_2_fanIn_reg_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1978 | `npi_nl_sig_2_fanIn_reg_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1982 | `npi_nl_sig_2_fanOut_reg_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1986 | `npi_nl_sig_2_fanOut_reg_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1989 | `npi_nl_sig_2_mod_inst_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1994 | `npi_nl_sig_2_mod_inst_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 1998 | `npi_nl_sig_2_primitive_inst_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2002 | `npi_nl_sig_2_primitive_inst_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2006 | `npi_nl_sig_2_reg_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2010 | `npi_nl_sig_2_reg_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2014 | `npi_nl_sig_2_sig_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2018 | `npi_nl_sig_2_sig_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2023 | `npi_nl_sig_hdl_2_fanIn_reg_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2027 | `npi_nl_sig_hdl_2_fanIn_reg_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2030 | `npi_nl_sig_hdl_2_fanOut_reg_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2034 | `npi_nl_sig_hdl_2_fanOut_reg_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2038 | `npi_nl_sig_hdl_2_mod_inst_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2042 | `npi_nl_sig_hdl_2_mod_inst_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2046 | `npi_nl_sig_hdl_2_primitive_inst_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2050 | `npi_nl_sig_hdl_2_primitive_inst_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2054 | `npi_nl_sig_hdl_2_reg_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2058 | `npi_nl_sig_hdl_2_reg_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2062 | `npi_nl_sig_hdl_2_sig_hdl_conn` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |
| 2067 | `npi_nl_sig_hdl_2_sig_hdl_conn_dump` | 部分覆盖 | `port.trace/module.inspect` | Language Model 端口 high/low connection 完整；复杂跨模型 mapping 为部分 |

### NPI Library: Find

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2072 | `npi_find_inst_regex` | 未开放 | `-` | 通用 regex/wildcard find 尚未开放 |
| 2074 | `npi_find_inst_regex_dump` | 未开放 | `-` | 通用 regex/wildcard find 尚未开放 |
| 2077 | `npi_find_inst_wildcard` | 未开放 | `-` | 通用 regex/wildcard find 尚未开放 |
| 2079 | `npi_find_inst_wildcard_dump` | 未开放 | `-` | 通用 regex/wildcard find 尚未开放 |
| 2081 | `npi_find_inst_with_def_regex` | 完整覆盖 | `module.find_instances` | 按 module definition 查全部实例 |
| 2084 | `npi_find_inst_with_def_regex_dump` | 完整覆盖 | `module.find_instances` | 按 module definition 查全部实例 |
| 2086 | `npi_find_inst_with_def_wildcard` | 完整覆盖 | `module.find_instances` | 按 module definition 查全部实例 |
| 2088 | `npi_find_inst_with_def_wildcard_dump` | 完整覆盖 | `module.find_instances` | 按 module definition 查全部实例 |
| 2091 | `npi_find_signal_regex` | 未开放 | `-` | 通用 regex/wildcard find 尚未开放 |
| 2093 | `npi_find_signal_regex_dump` | 未开放 | `-` | 通用 regex/wildcard find 尚未开放 |
| 2096 | `npi_find_signal_wildcard` | 未开放 | `-` | 通用 regex/wildcard find 尚未开放 |
| 2098 | `npi_find_signal_wildcard_dump` | 未开放 | `-` | 通用 regex/wildcard find 尚未开放 |

### NPI Library: VANL Library

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2102 | `npi_vanl_begin` | 未开放 | `-` | 无 VANL value propagation session |
| 2105 | `npi_vanl_end` | 未开放 | `-` | 无 VANL value propagation session |
| 2107 | `npi_vanl_set_value` | 未开放 | `-` | 无 VANL value propagation session |
| 2109 | `npi_vanl_set_value_by_hdl` | 未开放 | `-` | 无 VANL value propagation session |
| 2111 | `npi_vanl_set_value_from_file` | 未开放 | `-` | 无 VANL value propagation session |
| 2113 | `npi_vanl_propagate_value` | 未开放 | `-` | 无 VANL value propagation session |
| 2115 | `npi_vanl_get_value` | 未开放 | `-` | 无 VANL value propagation session |
| 2117 | `npi_vanl_get_value_by_hdl` | 未开放 | `-` | 无 VANL value propagation session |
| 2119 | `npi_vanl_dump_value_to_file` | 未开放 | `-` | 无 VANL value propagation session |
| 2122 | `npi_vanl_clear_all_value` | 未开放 | `-` | 无 VANL value propagation session |
| 2124 | `npi_vanl_driver` | 未开放 | `-` | 无 VANL value propagation session |
| 2127 | `npi_vanl_driver_by_hdl` | 未开放 | `-` | 无 VANL value propagation session |
| 2131 | `npi_vanl_driver_dump` | 未开放 | `-` | 无 VANL value propagation session |
| 2134 | `npi_vanl_driver_by_hdl_dump` | 未开放 | `-` | 无 VANL value propagation session |
| 2137 | `npi_vanl_load` | 未开放 | `-` | 无 VANL value propagation session |
| 2140 | `npi_vanl_load_by_hdl` | 未开放 | `-` | 无 VANL value propagation session |
| 2143 | `npi_vanl_load_dump` | 未开放 | `-` | 无 VANL value propagation session |
| 2146 | `npi_vanl_load_by_hdl_dump` | 未开放 | `-` | 无 VANL value propagation session |
| 2149 | `npi_vanl_fan_in_reg` | 未开放 | `-` | 无 VANL value propagation session |
| 2153 | `npi_vanl_fan_in_reg_by_hdl` | 未开放 | `-` | 无 VANL value propagation session |
| 2156 | `npi_vanl_fan_in_reg_dump` | 未开放 | `-` | 无 VANL value propagation session |
| 2159 | `npi_vanl_fan_in_reg_by_hdl_dump` | 未开放 | `-` | 无 VANL value propagation session |
| 2163 | `npi_vanl_fan_out_reg` | 未开放 | `-` | 无 VANL value propagation session |
| 2166 | `npi_vanl_fan_out_reg_by_hdl` | 未开放 | `-` | 无 VANL value propagation session |
| 2169 | `npi_vanl_fan_out_reg_dump` | 未开放 | `-` | 无 VANL value propagation session |
| 2172 | `npi_vanl_fan_out_reg_by_hdl_dump` | 未开放 | `-` | 无 VANL value propagation session |
| 2176 | `npi_vanl_report_all_path` | 未开放 | `-` | 无 VANL value propagation session |

### NPI Library: FSDB Library

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2181 | `npi_fsdb_convert_time_in` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2183 | `npi_fsdb_convert_time_out` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2185 | `npi_fsdb_dump_sig_hdl_value_between` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2187 | `npi_fsdb_dump_sig_value_between` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2190 | `npi_fsdb_hier_tree_dump_scope` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2193 | `npi_fsdb_hier_tree_dump_sig` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2196 | `npi_fsdb_sig_find_value_backward` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2198 | `npi_fsdb_sig_find_value_forward` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2201 | `npi_fsdb_sig_find_x_backward` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2203 | `npi_fsdb_sig_find_x_forward` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2206 | `npi_fsdb_sig_hdl_find_value_backward` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2208 | `npi_fsdb_sig_hdl_find_value_forward` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2211 | `npi_fsdb_sig_hdl_find_x_backward` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2213 | `npi_fsdb_sig_hdl_find_x_forward` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2215 | `npi_fsdb_sig_hdl_value_at` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2217 | `npi_fsdb_sig_hdl_value_between` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2220 | `npi_fsdb_sig_hdl_vc_count` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2222 | `npi_fsdb_sig_hdl_vec_value_at` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2225 | `npi_fsdb_sig_value_at` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2227 | `npi_fsdb_sig_value_between` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2230 | `npi_fsdb_sig_vc_count` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2232 | `npi_l1_fsdb_sig_by_property` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2235 | `npi_l1_fsdb_sig_by_property (with given FSDB handle)` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2239 | `npi_l1_fsdb_sig_by_property (with given signal vector)` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2243 | `npi_l1_fsdb_sig_by_property_message` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2245 | `npi_fsdb_sig_vec_value_at` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |
| 2248 | `npi_fsdb_time_scale_unit` | 部分覆盖 | `scope.list/signal.info/value.at/signal.scan` | 常用 signal FSDB 任务已覆盖 |

### NPI Library: Power Library

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2250 | `npi_pw_get_domain_crossing_pd` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2256 | `npi_pw_get_domain_crossing_path` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2266 | `npi_pw_get_domain_crossing_path_through_ports` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2273 | `npi_pw_get_domain_crossing_path_by_pd` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2282 | `npi_pw_get_domain_crossing_path_through_pds` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2292 | `npi_pw_get_domain_crossing_path_by_pd_hdl` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2301 | `npi_pw_get_domain_crossing_path_through_pd_hdls` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2309 | `npi_pw_get_all_domain_crossing_path` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2317 | `npi_pw_domain_crossing_path_by_pd_dump` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2325 | `npi_pw_domain_crossing_path_through_pds_dump` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2332 | `npi_pw_domain_crossing_path_by_hdl_dump` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2339 | `npi_pw_domain_crossing_path_through_pd_hdls_dum p` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2347 | `npi_pw_all_domain_crossing_path_dump` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2353 | `npi_pw_domain_crossing_path_dump` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2361 | `npi_pw_get_pd_from_inst` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2366 | `npi_pw_get_primary_power_net_from_inst` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2369 | `npi_pw_get_primary_ground_net_from_inst` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2373 | `npi_pw_get_pd_from_primary_power_net` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2378 | `npi_pw_get_pd_from_primary_ground_net` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2382 | `npi_pw_get_boundary_inst_from_pd` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2387 | `npi_pw_trace_supply_driver` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2392 | `npi_pw_trace_supply_load` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2396 | `npi_pw_get_supply_network_path` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2401 | `npi_pw_get_primary_power_network_path` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2406 | `npi_pw_get_primary_ground_network_path` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2411 | `npi_pw_supply_network_path_dump` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |
| 2416 | `npi_pw_primary_power_ground_network_path_dump` | 许可证阻塞 | `power.resolve/power.list` | 实现受当前 VM PowerAwareAnalysis license 阻塞 |

### NPI Library: FSDB Transaction Writer

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2422 | `npi_tr_writer_new` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2427 | `flush_writer` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2430 | `create_object` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2436 | `end_object` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2439 | `set_object_parent` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2444 | `add_if_path` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2448 | `add_object_child` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2452 | `add_object_children` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2457 | `set_object_predecessor` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2462 | `add_object_successor` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2467 | `add_object_successors` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2472 | `set_object_attribute_value_bit` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2478 | `set_object_attribute_value_bit_vector` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2484 | `set_object_attribute_value_int` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2490 | `set_object_attribute_value_real` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2494 | `set_object_attribute_value_time` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2499 | `set_object_attribute_value_string` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2503 | `npi_tr_writer_create_bit_vector_value` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2505 | `npi_tr_writer_FSDB_open` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2509 | `npi_tr_writer_FSDB_close` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |
| 2511 | `npi_tr_writer_incr_time` | 部分覆盖 | `transaction.writer.create` | 常用 writer object/attribute/relation 子集 |

### NPI Library: Hierarchy Tree

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2515 | `npi_hier_tree_dump_csv` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2518 | `npi_hier_tree_dump_txt` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2520 | `npi_hier_tree_trv` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2524 | `npi_hier_tree_trv_begin` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2527 | `npi_hier_tree_trv_block` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2529 | `npi_hier_tree_trv_for` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2533 | `npi_hier_tree_trv_class_defn` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2536 | `npi_hier_tree_trv_fork` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2539 | `npi_hier_tree_trv_gen_scope` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2542 | `npi_hier_tree_trv_generate` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2546 | `npi_hier_tree_trv_inst` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2549 | `npi_hier_tree_trv_named_begin` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2552 | `npi_hier_tree_trv_named_fork` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2556 | `npi_hier_tree_trv_register_cb` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2560 | `npi_hier_tree_trv_reset_cb` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2563 | `npi_hier_tree_trv_subprogram` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2566 | `npi_hier_tree_trv_task_func` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2569 | `npi_nl_hier_tree_trv` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2573 | `npi_nl_hier_tree_trv_register_cb` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2577 | `npi_nl_hier_tree_trv_reset_cb` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |

### NPI Library: List

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2581 | `npi_list_all_arch_body` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2584 | `npi_list_all_entity` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2587 | `npi_list_all_module_define` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2589 | `npi_nl_list_all_register` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2591 | `npi_nl_list_all_register_hdl` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2594 | `npi_nl_list_all_tristate` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2596 | `npi_nl_list_all_tristate_hdl` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |

### NPI Library: Component

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2598 | `npi_arch_body_dump_fileName_lineNo` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2601 | `npi_arch_body_dump_inst` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2604 | `npi_arch_body_get_inst` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2607 | `npi_comp_dump_block` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2610 | `npi_comp_dump_component` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2613 | `npi_comp_dump_component_in_generate` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2616 | `npi_comp_dump_fileName_lineNo` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2619 | `npi_comp_dump_func` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2623 | `npi_comp_dump_generate` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2626 | `npi_comp_dump_generic` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2629 | `npi_comp_dump_lang_interface` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2633 | `npi_comp_dump_port` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2636 | `npi_comp_dump_proc` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2640 | `npi_comp_dump_sig` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2643 | `npi_comp_dump_var` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2646 | `npi_comp_get_block` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2650 | `npi_comp_get_component` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2653 | `npi_comp_get_component_in_generate` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2656 | `npi_comp_get_conc_assert` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2660 | `npi_comp_get_conc_proc_call` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2663 | `npi_comp_get_conc_sig_assign` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2667 | `npi_comp_get_func` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2670 | `npi_comp_get_generate` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2674 | `npi_comp_get_generic` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2677 | `npi_comp_get_lang_interface` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2681 | `npi_comp_get_port` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2684 | `npi_comp_get_proc` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2688 | `npi_comp_get_process` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2692 | `npi_comp_get_sig` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2695 | `npi_comp_get_var` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2698 | `npi_entity_dump_fileName_lineNo` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2701 | `npi_entity_dump_inst` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |
| 2704 | `npi_entity_get_inst` | 部分覆盖 | `module.inspect/scope.list/trace.graph` | 公开任务覆盖常用层次读取，不暴露 callback/list handle |

### NPI Library: Miscellaneous

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2708 | `npi_arg_add_attr` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2709 | `npi_arg_attr_append_value` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2710 | `npi_arg_attr_get_value` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2711 | `npi_arg_attr_has_value` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2711 | `npi_arg_attr_number_value` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2712 | `npi_arg_attr_remove_value` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2712 | `npi_arg_construct` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2713 | `npi_arg_destroy` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2713 | `npi_arg_get_argc` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2714 | `npi_arg_get_argv` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2714 | `npi_arg_has_attr` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2715 | `npi_arg_number_attr` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2715 | `npi_arg_remove_attr` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2716 | `npi_communicate_novas_add_event_callback` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2718 | `npi_communicate_novas_begin` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2719 | `npi_communicate_novas_call_command` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2720 | `npi_communicate_novas_check_for_events` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2720 | `npi_communicate_novas_end` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2721 | `npi_communicate_is_connected` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2721 | `npi_socket_client_call_command` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2724 | `npi_socket_client_check_connect` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2724 | `npi_socket_client_connect` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2725 | `npi_socket_client_construct` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2726 | `npi_socket_client_destroy` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2726 | `npi_socket_client_get_free_port` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2726 | `npi_socket_client_is_port_free` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2727 | `npi_socket_client_set_abort_callback` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2728 | `npi_usn_back` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2730 | `npi_usn_construct` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2731 | `npi_usn_delimiter` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2732 | `npi_usn_destroy` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2732 | `npi_usn_hierarchy_name` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2733 | `npi_usn_is_empty` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2734 | `npi_usn_middle_name` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2735 | `npi_usn_number` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2736 | `npi_usn_pop_back` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2737 | `npi_usn_push_back` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2738 | `npi_usn_scope_name_at` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |
| 2739 | `npi_usn_set_delimiter` | 部分覆盖 | `language.resolve/module.inspect` | 表达式反编译和常用 HDL 元信息已输出 |

### NPI Library: Module

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2741 | `npi_mod_define_dump_fileName_lineNo` | 完整覆盖 | `module.find_instances` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2743 | `npi_mod_define_dump_inst` | 完整覆盖 | `module.find_instances` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2745 | `npi_mod_define_get_inst` | 完整覆盖 | `module.find_instances` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2747 | `npi_mod_inst_dump_cont_assign` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2749 | `npi_mod_inst_dump_fileName_lineNo` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2751 | `npi_mod_inst_dump_func` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2753 | `npi_mod_inst_dump_gen_scope` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2756 | `npi_mod_inst_dump_instance` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2758 | `npi_mod_inst_dump_instance_in_gen_scope` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2760 | `npi_mod_inst_dump_io` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2763 | `npi_mod_inst_dump_lang_interface` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2766 | `npi_mod_inst_dump_net` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2768 | `npi_mod_inst_dump_parameter` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2770 | `npi_mod_inst_dump_port` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2772 | `npi_mod_inst_dump_primitive` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2775 | `npi_mod_inst_dump_task` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2777 | `npi_mod_inst_dump_var` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2779 | `npi_mod_inst_get_cont_assign` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2782 | `npi_mod_inst_get_func` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2784 | `npi_mod_inst_get_gen_scope` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2786 | `npi_mod_inst_get_instance` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2789 | `npi_mod_inst_get_instance_in_gen_scope` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2791 | `npi_mod_inst_get_io` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2794 | `npi_mod_inst_get_lang_interface` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2797 | `npi_mod_inst_get_net` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2799 | `npi_mod_inst_get_parameter` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2802 | `npi_mod_inst_get_port` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2804 | `npi_mod_inst_get_primitive` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2806 | `npi_mod_inst_get_process_always` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2809 | `npi_mod_inst_get_process_init` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2811 | `npi_mod_inst_get_task` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |
| 2813 | `npi_mod_inst_get_var` | 完整覆盖 | `module.objects/module.inspect` | JSON 字段替代 stdout dump；15 类 getter 均有固定 kind 映射 |

### NPI Library: Netlist Library

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2817 | `npi_nl_inst_handle_by_nl_name` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2821 | `npi_nl_instport_2_port` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2824 | `npi_nl_instport_handle_by_nl_name` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2828 | `npi_nl_L1_handle_by_name` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2831 | `npi_nl_net_2_port_instport` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2835 | `npi_nl_net_handle_by_nl_name` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2839 | `npi_nl_pass_assign_cell` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2842 | `npi_nl_pass_primitive_cell` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2845 | `npi_nl_port_2_instport` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2848 | `npi_nl_port_handle_by_nl_name` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2852 | `npi_nl_port_instport_2_net` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |
| 2857 | `npi_nl_sig_handle_by_name` | 部分覆盖 | `netlist.resolve/netlist.iterate` | 对象查找/遍历已覆盖，all-path/fanin/fanout 尚未开放 |

### NPI Library: Signal

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 2861 | `npi_nl_bit_trace_driver_by_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2871 | `npi_nl_bit_trace_driver_by_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2881 | `npi_nl_bit_trace_load_by_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2891 | `npi_nl_bit_trace_load_by_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2901 | `npi_nl_dump_equivalent_signal` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2904 | `npi_nl_dump_equivalent_signal_by_hdl` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2907 | `npi_dump_signal_define_typespec` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2909 | `npi_dump_signal_define_typespec_by_hdl` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2911 | `npi_get_sig_elem_range` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2915 | `npi_get_bit_blasted_signal` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2918 | `npi_dump_signal_define_typespec_by_hdl` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2920 | `npi_nl_get_equivalent_signal` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2923 | `npi_nl_get_equivalent_signal_by_hdl` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2926 | `npi_get_signal_define_typespec` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2928 | `npi_get_signal_define_typespec_by_hdl` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 2930 | `npi_nl_trace_driver` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2934 | `npi_nl_trace_driver_by_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2937 | `npi_nl_trace_driver_by_hdl2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2942 | `npi_nl_trace_driver_by_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2946 | `npi_nl_trace_driver_by_hdl_dump2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2951 | `npi_nl_trace_driver_by_inst_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2955 | `npi_nl_trace_driver_by_inst_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2958 | `npi_nl_trace_driver_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2962 | `npi_nl_trace_load` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2965 | `npi_nl_trace_load_by_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2969 | `npi_nl_trace_load_by_hdl2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2974 | `npi_nl_trace_load_by_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2977 | `npi_nl_trace_load_by_hdl_dump2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2982 | `npi_nl_trace_load_by_inst_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2986 | `npi_nl_trace_load_by_inst_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2989 | `npi_nl_trace_load_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 2993 | `npi_nl_trace_network_port_2_inst` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3016 | `npi_nl_trace_network_sig_2_sig` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3026 | `npi_nl_trace_network_sig_2_inst` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3033 | `npi_nl_trace_network_of_ordered_instance` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3038 | `npi_nl_report_all_path` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 3043 | `npi_nl_clear_network` | 部分覆盖 | `signal.resolve/port.trace/interface.resolve` | 常用信号与端口映射已覆盖 |
| 3043 | `npi_trace_driver` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3046 | `npi_trace_driver_by_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3048 | `npi_trace_driver_by_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3050 | `npi_trace_driver_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3052 | `npi_trace_load` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3055 | `npi_trace_load_by_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3057 | `npi_trace_load_by_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3059 | `npi_trace_load_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3061 | `npi_trace_driver_by_hdl_dump2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3066 | `npi_trace_driver_by_hdl2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3073 | `npi_trace_driver_dump2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3077 | `npi_trace_driver2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3083 | `npi_trace_load_by_hdl_dump2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3088 | `npi_trace_load_by_hdl2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3095 | `npi_trace_load_dump2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3099 | `npi_trace_load2` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3104 | `npi_active_trace_driver` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3110 | `npi_active_trace_driver_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3114 | `npi_active_trace_driver_by_hdl` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |
| 3120 | `npi_active_trace_driver_by_hdl_dump` | 完整覆盖 | `trace.driver/trace.load/trace.active_driver` | 静态与 active trace 使用 Tcl NPI |

### NPI Library: Utilities

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 3125 | `npi_expr_decompile` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3127 | `npi_expr_trv` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3129 | `npi_expr_trv_register_cb` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3132 | `npi_expr_trv_reset_cb` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3134 | `npi_nl_ut_dump_hdl_info` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3137 | `npi_nl_ut_dump_hdl_vec_info` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3139 | `npi_nl_ut_filter_port_instport` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3142 | `npi_nl_register_func_cb` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3145 | `npi_nl_reset_func_cb` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3147 | `npi_nl_ut_get_actual_is_literal` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3151 | `npi_nl_ut_get_actual_name` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3153 | `npi_nl_ut_get_actual_name_vec` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3156 | `npi_nl_ut_get_actual_value` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3161 | `npi_nl_ut_get_hdl_info` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3163 | `npi_nl_ut_verbose_dump` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3166 | `npi_nl_ut_get_hdl_by_actual_name` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3169 | `npi_ut_dump_hdl_info` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3171 | `npi_ut_dump_hdl_vec_info` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3174 | `npi_ut_get_hdl_info` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3177 | `npi_ut_is_signal` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3179 | `npi_ut_get_typespec_size` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3181 | `npi_ut_get_typespec_hdl` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3184 | `npi_ut_fsdb_bin_str_2_vanl_str` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |
| 3186 | `npi_ut_verbose_dump` | 等价覆盖 | `KDebug JSON CLI/session` | 参数、通信、生命周期由 KDebug 协议层提供 |

### NPI Library: CRDB Library

| 页码 | API/手册条目 | 判定 | KVerif action | 对照说明 |
| ---: | --- | --- | --- | --- |
| 3190 | `npi_crdb_hier_tree_trv` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3192 | `npi_crdb_hier_tree_trv_register_cb` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3195 | `npi_crdb_hier_tree_trv_reset_cb` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3197 | `npi_crdb_list_scope` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3200 | `npi_crdb_list_sig` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3204 | `npi_crdb_list_flatten_sig` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3207 | `npi_crdb_corr_sig` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3210 | `npi_crdb_eq_sig` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3212 | `npi_crdb_dump_all_mapping` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3214 | `npi_crdb_dump_mapping` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3217 | `npi_crdb_clean_correlation` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3219 | `npi_crdb_set_correlation_by_mapping_file` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3221 | `npi_crdb_init_opt` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3224 | `npi_crdb_get_hdl_info` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3226 | `npi_crdb_dump_hdl_info` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
| 3228 | `npi_crdb_dump_hdl_vec_info` | 部分覆盖 | `crdb.resolve/crdb.correlates` | 读取与 correlation 覆盖，写 mapping 未开放 |
