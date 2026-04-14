# Automotive Factory Feature Roadmap

This document captures three high-value features that can extend the manufacturing analytics assistant into a more automotive-specific production intelligence tool.

## 1. OEE and Bottleneck Intelligence

Purpose:
Show where availability, performance, and quality are being lost across lines, shifts, and stations.

Business value:
- Gives plant managers a direct effectiveness KPI instead of only raw anomaly lists.
- Highlights the weakest lines and stations quickly.
- Connects downtime, throughput, and quality loss into one operational view.

Suggested data fields:
- `line_id`
- `station_id`
- `shift`
- `planned_production_minutes`
- `good_units`
- `reject_units`
- `ideal_cycle_time_seconds`

Suggested product capabilities:
- Overall and by-line OEE dashboards
- Shift and station bottleneck ranking
- Benchmark comparison against target OEE
- Agent-generated explanation of the main loss driver
- Suggested countermeasures for the weakest line

Implementation status:
- Started on branch `feature-automotive-oee-dashboard`
- Initial backend, dashboard, and PDF support are part of this implementation slice

## 2. Predictive Maintenance and Downtime Root Cause Tracking

Purpose:
Predict likely failures and explain repeated stoppages before they turn into line-wide disruption.

Business value:
- Reduces unplanned downtime
- Helps maintenance teams prioritize the highest-risk assets
- Improves spare-part and service planning

Suggested data fields:
- `vibration_mm_s`
- `pressure_bar`
- `power_draw_kw`
- `alarm_code`
- `maintenance_date`
- `maintenance_type`
- `failure_mode`
- `component_id`

Suggested product capabilities:
- Machine health scoring
- Repeated stoppage clustering by root cause
- Early warning alerts for rising failure likelihood
- Maintenance recommendations with urgency and expected downtime avoidance
- Historical recall of similar machine failures using workflow memory

## 3. Quality Traceability and Scrap/Rework Analysis

Purpose:
Trace defects and scrap patterns back to lines, stations, shifts, and suppliers.

Business value:
- Supports containment decisions during quality escapes
- Helps isolate recurring scrap drivers
- Links process drift to business cost and throughput loss

Suggested data fields:
- `part_number`
- `batch_id`
- `supplier_id`
- `defect_type`
- `scrap_count`
- `rework_count`
- `vin` or `production_lot`

Suggested product capabilities:
- Defect hotspot maps by line, shift, and supplier
- Scrap and rework trend reporting
- Root-cause narratives tied to affected part families
- Suggested containment and corrective action plans
- PDF exports for quality review meetings

## Recommended Build Order

1. OEE and Bottleneck Intelligence
2. Predictive Maintenance and Downtime Root Cause Tracking
3. Quality Traceability and Scrap/Rework Analysis

This order gives the fastest visible value in demos while keeping the data model extensible for deeper automotive use cases.
