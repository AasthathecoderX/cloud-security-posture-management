\# Phase 6 — Attack Path Analysis



\## 1. Overview



Phase 6 introduces backend attack-path analysis for cloud security findings.



The implementation builds a directed graph from normalized cloud resources and supported relationships. It then performs bounded path discovery from Internet-exposed resources to downstream sensitive resources.



The implementation is designed to avoid inventing relationships that are not supported by the collected cloud data.



\---



\## 2. Member 3 Scope



The Member 3 implementation includes:



\* EC2 instance collection

\* IAM role attachment collection

\* EC2 resource mapping

\* IAM role attachment mapping

\* Attack-path graph construction

\* Supported relationship generation

\* Bounded attack-path discovery

\* Attack-path API endpoint

\* Attack-path unit tests

\* Attack-path API test

\* Frontend response format for M4 integration



\---



\## 3. Cloud Collector Extensions



\### 3.1 EC2 Instance Collection



The collector uses the AWS EC2 `describe\_instances()` API.



Normalized EC2 resources include:



\* Instance ID

\* Public IP address

\* Private IP address

\* Security-group IDs

\* IAM instance-profile ARN



Resource type:



```text

ec2\_instance

```



The collector handles individual invalid EC2 resources without stopping the complete collection.



\---



\### 3.2 IAM Role Attachments



The collector retrieves IAM roles using:



```text

list\_roles

```



For each role, the collector retrieves:



```text

list\_attached\_role\_policies

list\_instance\_profiles\_for\_role

```



The normalized IAM role resource contains:



\* Role name

\* Role ARN

\* Attached policy ARNs

\* Instance profile ARNs

\* Supported relationship information



Resource type:



```text

iam\_role

```



If an individual role cannot be processed, the collector logs the problem and continues processing other roles.



\---



\## 4. Resource Mapping



Two resource mappers were added for the Phase 6 collector extension.



\### EC2 Mapper



The EC2 mapper converts AWS EC2 instance information into the normalized Contract A resource format.



The normalized resource contains:



```text

resource\_id

resource\_type

public\_ip

private\_ip

security\_groups

iam\_instance\_profile\_arn

```



\### IAM Role Mapper



The IAM role mapper converts role, attached-policy, and instance-profile information into normalized data.



The normalized resource contains:



```text

resource\_id

resource\_type

role\_arn

attached\_policy\_arns

instance\_profile\_arns

relationships

```



\---



\## 5. Supported Graph Relationships



The attack-path implementation supports the following relationships:



| Source       | Target       | Relationship     |

| ------------ | ------------ | ---------------- |

| EC2 instance | IAM role     | `ASSUMES`        |

| IAM role     | IAM policy   | `HAS\_PERMISSION` |

| IAM policy   | S3 bucket    | `ACCESSES`       |

| Internet     | EC2 instance | `EXPOSES`        |



Only relationships supported by normalized resource data are generated.



The implementation does not create unsupported relationships simply because two resources exist.



\---



\## 6. Attack-Path Graph



The backend uses:



```text

networkx.DiGraph

```



to construct the attack-path graph internally.



Graph nodes represent cloud resources.



Graph edges represent supported relationships.



NetworkX objects are used only internally and are never exposed through the API.



The API returns normal JSON-compatible objects.



\---



\## 7. Internet Exposure



Internet exposure is derived from security-group ingress information.



A security group is considered publicly exposed when its ingress data contains:



```text

0.0.0.0/0

```



If that security group is attached to an EC2 instance, the following relationship is created:



```text

Internet → EC2 Instance

```



with:



```text

EXPOSES

```



Private security groups do not generate an `EXPOSES` relationship.



\---



\## 8. Attack-Path Discovery



Attack paths start from the derived:



```text

internet

```



entry point.



The path finder searches for downstream sensitive resources using only relationships present in the graph.



Supported sensitive resource types include:



```text

iam\_role

s3\_bucket

```



A sensitive resource is considered a final path target when it has no supported downstream relationships.



This prevents an intermediate IAM role from being reported as a completed attack path when a longer supported path continues to a downstream resource.



\---



\## 9. Bounded Path Search



Attack-path discovery is explicitly bounded.



Default configuration:



```text

cutoff = 5

max\_paths = 100

```



\### Cutoff



The cutoff limits the maximum number of graph edges in a discovered path.



\### Maximum paths



The maximum path limit prevents excessive results when the graph contains many possible paths.



The implementation uses NetworkX `all\_simple\_paths()` with an explicit cutoff and maximum result limit.



Unbounded graph traversal is not used.



\---



\## 10. Attack-Path API



The API endpoint is:



```text

GET /scans/{scan\_id}/attack-paths

```



The endpoint performs the following steps:



1\. Loads the requested scan.

2\. Verifies scan ownership.

3\. Loads findings associated with the scan.

4\. Loads available normalized cloud resources.

5\. Builds the attack-path graph.

6\. Converts graph relationships into API-safe links.

7\. Finds bounded attack paths.

8\. Associates findings with matching resource IDs.

9\. Returns the attack-path response.



\---



\## 11. API Response Format



The endpoint returns the following structure:



```json

{

&#x20; "scan\_id": "123",

&#x20; "nodes": \[

&#x20;   {

&#x20;     "id": "i-001",

&#x20;     "type": "ec2\_instance",

&#x20;     "label": "EC2 Instance (i-001)",

&#x20;     "severity": "High",

&#x20;     "risk\_score": 92,

&#x20;     "finding\_id": "finding-1"

&#x20;   },

&#x20;   {

&#x20;     "id": "demo-role",

&#x20;     "type": "iam\_role",

&#x20;     "label": "IAM Role (demo-role)",

&#x20;     "severity": null,

&#x20;     "risk\_score": null,

&#x20;     "finding\_id": null

&#x20;   }

&#x20; ],

&#x20; "links": \[

&#x20;   {

&#x20;     "source": "internet",

&#x20;     "target": "i-001",

&#x20;     "relationship": "EXPOSES"

&#x20;   },

&#x20;   {

&#x20;     "source": "i-001",

&#x20;     "target": "demo-role",

&#x20;     "relationship": "ASSUMES"

&#x20;   }

&#x20; ],

&#x20; "paths": \[]

}

```



\### Node information



Each node can contain:



\* Resource ID

\* Resource type

\* Display label

\* Finding severity

\* Risk score

\* Finding ID



\### Link information



Each link contains:



\* Source

\* Target

\* Relationship



\### Path information



Each attack path contains:



\* Path ID

\* Ordered node IDs

\* Path severity



\---



\## 12. Finding Linkage



Attack-path nodes are linked to stored findings using the normalized resource ID.



When a finding exists for a resource, the API preserves:



```text

severity

risk\_score

finding\_id

```



This allows the frontend to display security context together with the graph.



If a supporting graph resource does not have a finding, its finding-related fields remain `null`.



\---



\## 13. Static Scan Behavior



Static scans currently store findings but do not persist the complete normalized cloud relationship graph in the database.



Therefore, the attack-path implementation does not invent relationships for static scans.



For static scans:



\* Nodes are derived from stored findings.

\* Unsupported relationships are not created.

\* No attack path is claimed unless the required relationship data exists.



This ensures that the API does not report unsupported attack paths.



\---



\## 14. Live Scan Behavior



For live scans, the attack-path endpoint can collect the current normalized cloud resources and use them to construct the graph.



This provides access to relationship information such as:



```text

EC2 → IAM Role

IAM Role → IAM Policy

Internet → EC2

```



Only relationships available from the collector data are used.



\---



\## 15. Error Handling



The collector handles individual resource failures without stopping the entire collection process.



The attack-path route also prevents cloud-provider-specific exceptions from being exposed directly through the API.



The API returns a controlled response even when cloud collection cannot provide relationship data.



\---



\## 16. Security and Correctness Guardrails



The implementation follows these guardrails:



\* No unsupported relationships are fabricated.

\* No unbounded attack-path traversal is performed.

\* Duplicate edges are removed.

\* Private security groups do not create Internet exposure edges.

\* Scan ownership is enforced using the existing scan authorization logic.

\* Finding information remains linked to matching resource IDs.

\* NetworkX internals are not exposed through the API.

\* Attack paths are bounded by cutoff and maximum-path limits.



\---



\## 17. Testing



The following attack-path tests were implemented.



\### Edge tests



\* Supported relationship generation

\* Private security-group behavior

\* Duplicate relationship removal



\### Graph tests



\* Attack graph construction

\* Graph-to-API link conversion



\### Path tests



\* Valid attack-path discovery

\* No attack-path case

\* Path cutoff enforcement

\* Maximum path limit enforcement



\### API test



The API test verifies:



\* Endpoint availability

\* Scan ownership

\* Node generation

\* Finding linkage

\* Severity

\* Risk score

\* Supported relationships

\* Response structure



Current test results:



```text

Collector tests: 14 passed

Attack-path tests: 9 passed

Attack-path API test: 1 passed

```



\---



\## 18. Frontend Integration



The frontend can consume:



```text

GET /scans/{scan\_id}/attack-paths

```



The response provides the data required to render:



\* Graph nodes

\* Graph relationships

\* Attack paths

\* Severity

\* Risk scores

\* Finding IDs



The frontend should treat the returned paths as bounded backend results.



\---



\## 19. Current Limitations



The current database schema does not persist the complete normalized cloud relationship graph for every scan.



Therefore:



\* Static scans expose finding-linked nodes without inventing relationships.

\* Live scans can rebuild relationship information through cloud collection.

\* Policy-to-S3 paths require explicit normalized relationship data.

\* The `ACCESSES` relationship is generated only when the required bucket relationship is actually present in normalized data.

\* Attack-path results represent relationships supported by the available scan/resource data.



These limitations are intentional to avoid claiming exploitability or relationships that cannot be established from the collected data.



\---



\## 20. Phase 6 Completion



Member 3 Phase 6 implementation includes:



\* EC2 collector extension

\* IAM role attachment collector extension

\* EC2 resource mapper

\* IAM role mapper

\* Attack-path graph

\* Attack-path edge builder

\* Bounded path finder

\* Attack-path API

\* Unit tests

\* API test

\* Frontend-compatible response format

\* Phase 6 documentation

\* Phase 6–7 metrics documentation



