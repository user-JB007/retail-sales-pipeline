# Service Report — Calculated Fields

```
// Within SLA (resolved)
[Resolved At] <= [SLA Due At]

// Age Hours (open tickets use as-of)
DATEDIFF('hour', [Opened At], IFNULL([Resolved At], TODAY()))

// Pending Flag
IF [Status] = "pending" OR [Status] = "escalated" THEN 1 ELSE 0 END

// Avg CSAT
AVG([CSAT])

// SLA Attainment %
SUM(IF [SLA Status] = "within_sla" THEN 1 ELSE 0 END)
/ SUM(IF [Is Open] = 0 THEN 1 ELSE 0 END)
```
