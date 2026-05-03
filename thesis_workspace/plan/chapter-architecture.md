# 章节架构锁定

## Required chapter files

- `chapters/01_introduction.md` | min_chars=6000 | owner=controller | placeholders=no
- `chapters/02_related_technology_and_requirements.md` | min_chars=7000 | owner=controller | placeholders=no
- `chapters/03_system_design.md` | min_chars=8000 | owner=controller | placeholders=no
- `chapters/04_detailed_design_and_implementation.md` | min_chars=11000 | owner=controller | placeholders=no
- `chapters/05_testing_and_results.md` | min_chars=8000 | owner=controller | placeholders=limited-until-real-results
- `chapters/06_conclusion.md` | min_chars=2500 | owner=controller | placeholders=no

## Supporting files

- `chapters/00_abstract.md` | after body chapters
- `chapters/acknowledgements.md` | after body chapters
- `refs/evidence-map.md` | before writing Chapter 1 and literature-driven parts
- `plan/experiment-protocol.md` | before writing Chapter 5
- `figures/data-manifest.md` | before creating data figures
- `tables/table-schema.md` | before filling result tables

## Quality gates

- 每章必须通过规范合规检查和质量检查。
- 引言和相关技术部分必须先完成 evidence map 和 paragraph blueprint。
- 测试与结果章节必须先完成实验协议、图表数据清单和表格 schema。
- 没有真实测试数据时，不得把规划数据写成实验结论。
