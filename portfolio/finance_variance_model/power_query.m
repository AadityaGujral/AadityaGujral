// Create a blank query named LoadTable; replace Folder with your generated path.
// Then create four queries using LoadTable("dim_month"), etc.
(TableName as text) as table =>
let
    Folder = "C:\\portfolio\\finance_variance_model\\generated\\",
    Records = Json.Document(File.Contents(Folder & TableName & ".json")),
    Result = Table.FromRecords(Records)
in
    Result
