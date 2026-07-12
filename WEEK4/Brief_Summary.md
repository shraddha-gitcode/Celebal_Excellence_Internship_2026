# End-to-End Data Pipeline using Azure Storage & Azure Data Factory

## Objective
Understand Azure cloud concepts and build an end-to-end data pipeline (Blob Storage → Azure Data Factory → Destination) with metadata validation, using the Superstore dataset.

## Architecture

```
[Local CSV: Sample - Superstore.csv]
            |
            v
   Azure Blob Storage (shraddhastorage001)
        Container: source
            |
            v
   Azure Data Factory (ADF-Shraddha)
   ┌─────────────────────────────┐
   │ Linked Service: LS_BlobStorage
   │ Dataset (Source): DelimitedText1 → /source
   │ Dataset (Sink):   DelimitedText2 → /destination
   │ Pipeline: BlobToBlobPipeline
   │   1. Get Metadata (validates file exists, size, lastModified)
   │   2. Copy Data (source → sink)
   └─────────────────────────────┘
            |
            v
   Azure Blob Storage (shraddhastorage001)
        Container: destination
        File: CopiedSuperstore.csv
```

## Resources Created

| Resource | Name | Region |
|---|---|---|
| Resource Group | RG-ADF-Lab | Central India |
| Storage Account | shraddhastorage001 | Central India |
| Blob Containers | source, destination, $logs | — |
| Data Factory | ADF-Shraddha (V2) | Central India |
| Linked Service | LS_BlobStorage (Azure Blob Storage) | — |
| Datasets | DelimitedText1 (source), DelimitedText2 (destination) | — |
| Pipeline | BlobToBlobPipeline | — |

## Execution Process

1. **Resource Group & Storage** – Created `RG-ADF-Lab`, deployed `shraddhastorage001` storage account, created `source` and `destination` blob containers, and uploaded `Sample - Superstore.csv` (2.18 MiB) to `source`.
2. **Azure Data Factory** – Provisioned `ADF-Shraddha` in the same resource group and opened ADF Studio (Author / Monitor / Manage).
3. **Linked Service** – Configured `LS_BlobStorage` to connect ADF to the storage account.
4. **Datasets** – Created `DelimitedText1` pointing to `/source` and `DelimitedText2` pointing to `/destination`, both using the `LS_BlobStorage` linked service, comma-delimited, UTF-8.
5. **Pipeline (BlobToBlobPipeline)**
   - **Get Metadata activity** – checks `Exists`, `Item name`, `Last modified`, `Size` on the source file.
   - **Copy Data activity** – chained after Get Metadata; source = `DelimitedText1`, sink = `DelimitedText2`.
   - An initial **Publish** attempt failed validation because the Copy activity's source/sink datasets hadn't been set yet — this was corrected before a successful publish.
6. **Execution & Monitoring** – Pipeline was run via manual trigger/debug. Both activities (`Get Metadata1`, `Copy data1`) succeeded. Monitor → Pipeline Runs confirms status **Succeeded**, duration 29s.
7. **Validation** – Destination container now contains `CopiedSuperstore.csv`, 2.18 MiB — identical size to the source file. Copy activity details confirm 2.288 MB read = 2.288 MB written, 1 file, throughput 1.144 MB/s.
8. **IAM / Access Control** – Reviewed Access Control (IAM) on the storage account; current role assignments show **Owner** (inherited from subscription). *(See "Gap" note below.)*

## Results

| Check | Result |
|---|---|
| Get Metadata output | `exists: true`, `itemName: Sample - Superstore.csv`, `size: 2287806 bytes` |
| Copy Data status | Succeeded |
| Source file size | 2.18 MiB |
| Destination file size | 2.18 MiB (match ✅) |
| Pipeline run status | Succeeded (29s, manual trigger) |

## Known Gap / Suggested Addition

The task asks to **assign IAM roles (Reader, Contributor)** to manage access between ADF and Storage. The current IAM screenshot only shows the **Owner** role inherited from the subscription — no explicit Reader or Contributor role assignment was captured. To fully close this requirement:
- Go to the Storage Account (or ADF resource) → **Access Control (IAM)** → **Add role assignment**.
- Assign **Reader** and/or **Contributor** to the ADF's managed identity or your user account.
- Screenshot the "Add role assignment" confirmation and the updated role assignments list.

Optionally, a screenshot of the Resource Group creation blade itself (rather than just resources landing inside it) would make the documentation fully complete end-to-end.

## Screenshots

All screenshots are provided in `/screenshots`, renamed in execution order:

1. `01_StorageAccount_Deployment_Success.png`
2. `02_BlobContainers_Created.png`
3. `03_Source_Container_CSV_Uploaded.png`
4. `04_ADF_Deployment_Success.png`
5. `05_ResourceGroup_Overview_ADF_Storage.png`
6. `06_ADF_Studio_Home_Overview.png`
7. `07_LinkedService_BlobStorage.png`
8. `08_Dataset_Source_DelimitedText1.png`
9. `09_Dataset_Destination_DelimitedText2.png`
10. `10_Pipeline_GetMetadata_Activity_Setup.png`
11. `11_Pipeline_Validation_Error_BeforeFix.png`
12. `12_Pipeline_CopyData_Sink_Configured_Published.png`
13. `13_Pipeline_GetMetadata_FieldList_Settings.png`
14. `14_Pipeline_Run_Succeeded_Debug.png`
15. `15_Monitor_PipelineRuns_List.png`
16. `16_Destination_CopiedFile_Overview.png`
17. `17_Destination_Container_File_Listing.png`
18. `18_CopyActivity_ExecutionDetails.png`
19. `19_IAM_AccessControl_RoleAssignments.png`
20. `20_GetMetadata_ActivityOutput_JSON.png`

## Submission Summary

An end-to-end data pipeline was implemented using Microsoft Azure. A Resource Group, Storage Account, Blob Containers, and Azure Data Factory were created successfully. The Superstore CSV dataset was uploaded to the source Blob container, and a Linked Service was configured to connect Azure Data Factory with Azure Blob Storage. Source and Destination Datasets were created, and a pipeline containing Get Metadata and Copy Data activities was developed. The pipeline was executed successfully using Trigger/Debug, and the execution was monitored through the Monitor tab. The Get Metadata activity validated the source file metadata, and the Copy Data activity successfully copied the CSV file from the source container to the destination container. IAM access was reviewed through Azure Access Control (IAM), completing the end-to-end Blob → ADF → Destination pipeline.
