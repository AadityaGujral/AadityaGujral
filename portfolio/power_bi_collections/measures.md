# Power BI DAX Measures

```DAX
Total Placed = SUM(Collections[original_balance])
Total Collected = SUM(Collections[amount_collected])
Outstanding Balance = SUM(Collections[current_balance])
Recovery Rate = DIVIDE([Total Collected],[Total Placed])
Accounts = DISTINCTCOUNT(Collections[account_id])
RPC Accounts = CALCULATE(DISTINCTCOUNT(Collections[account_id]), Collections[rpc_count] > 0)
RPC Rate = DIVIDE([RPC Accounts],[Accounts])
Dollars per RPC = DIVIDE([Total Collected], SUM(Collections[rpc_count]))
PTP Accounts = CALCULATE([Accounts], Collections[promise_to_pay] = 1)
PTP Rate = DIVIDE([PTP Accounts],[Accounts])
Settlement Accounts = CALCULATE([Accounts], Collections[settlement_flag] = 1)
Settlement Rate = DIVIDE([Settlement Accounts],[Accounts])
Default Rate = AVERAGE(Collections[default_flag])
90+ DPD Exposure = CALCULATE([Outstanding Balance], Collections[days_past_due] > 90)
```