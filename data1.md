anna runns 12 supermarket, every notght billing system writes days sales lines to a folder, head office has not data team an analyst opens the spreadsheet month ny month and writes total into a slide.
last week CFO asked oct month revenue and was gven 3 different figures, by 3 diff people all working on the same folder. manager asked the biscut pack sold in march by it was anaswered by the price on the shelf today

the CFO told that he wants something which can give oct revenue is oct, and he wants to slice revenue by store, by prtoduct, category,by day, by week, by month, he wants only 1 number not 3, also last march price shld be march. 

this is the structure of data:

├── data/
│   ├── billing_notes.md
│   ├── finance_monthly.csv
│   ├── masters.sql
│   ├── _truth/
│   │   ├── file_manifest.csv
│   │   └── truth.json
│   └── sales/... (600 csv files)

1.STAND THE PLATFORM UP AND LAND THE DATA: so bring up a relational db and a analytical query engine . load the daily files intop object storage, and organised so that a query abt one store in one month does not have to lookup at 11 stores or 11 months. say what organisation shld i chose and i need to show it working for one such query how many files n bytes could the engine possibly have to open under ur layouyt, compared with putting everything in one folder.

2.MAKE IT SAFE TO RUN TWICE: some days appear in the folder more than once, the billing system resends when a store reports a problem. build the loading setup so that the runnig it three tim3e sin arow gives the same result as running it once. help me prove it by running it 3 times and record the row count n check sum after each run.

3.DESIGN THE TABLES BVEHIND THE DASHBOARD: the dahsboard must slice revenue by store, by prtoduct, category,by day, by week, by month quickly. design n build the tables that make that possible without repeating each store nmae n address on millions of sales lines. notes 2 things abt the source data, niot every line is a sale and a product code that waas retired has since been reissued to a different product so the cose alone does not identify what was sold.

4.MAKE MARCH USE MARCH'S PRICE: Prices change. Using the revision table arrage things so that a report for march 2024 use the prices that applied in March 2024 while a report for last mont5h uses last months-- from the same query with no change to the code between the wo Demonstrate by running one query twice differing only in the reporting period.

5.QUERY ACROSS THE 2 SYSTEMS: The sales data in the objest store; the stores, products and categories are in the postgresSQL. Write one query that joins across both without first copying either side into other. Then tell us using evidence from the engine rather than from documentation,which parts of that query were evaluated where.

6.RECONCILE:Compare your monthly revenue against finance_momthly.csv. You will not match every month.For each month that differes, say whether the cause is something wrong with the source data, a difference in how the two of you define revenue, or a bug in your pipeline -- and say which of the three would take back to the finance team
