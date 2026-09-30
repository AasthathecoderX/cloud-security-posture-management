\# Phase 6–7 Metrics



\## 1. Purpose



This document defines the metrics used to evaluate the Phase 6 attack-path backend and provides a baseline for Phase 7 monitoring.



The metrics focus on:



\* Graph resource counts

\* Relationship counts

\* Attack-path counts

\* Path length

\* Bounded search behavior

\* API response time

\* Test coverage

\* Collection reliability



\---



\## 2. Graph Resource Metrics



For each scan, the following resource counts can be recorded:



| Metric          | Description                                        |

| --------------- | -------------------------------------------------- |

| Total resources | Total normalized resources used to build the graph |

| EC2 instances   | Number of `ec2\_instance` resources                 |

| IAM roles       | Number of `iam\_role` resources                     |

| IAM policies    | Number of `iam\_policy` resources                   |

| S3 buckets      | Number of `s3\_bucket` resources                    |

| Security groups | Number of `security\_group` resources               |



Example:



| Metric          | Example Value |

| --------------- | ------------: |

| Total resources |             4 |

| EC2 instances   |             1 |

| IAM roles       |             1 |

| IAM policies    |             1 |

| S3 buckets      |             0 |

| Security groups |             1 |



Example values are for illustration only and are not production measurements.



\---



\## 3. Relationship Metrics



The following relationship counts can be recorded:



| Relationship     | Description                               |

| ---------------- | ----------------------------------------- |

| `ASSUMES`        | EC2 instance to IAM role                  |

| `HAS\_PERMISSION` | IAM role to IAM policy                    |

| `ACCESSES`       | IAM policy to S3 bucket                   |

| `EXPOSES`        | Internet to publicly exposed EC2 instance |



Relationships must only be counted when supported by normalized resource data.



\---



\## 4. Attack-Path Metrics



For every scan, the following metrics can be recorded:



\* Number of discovered attack paths

\* Longest attack-path length

\* Number of paths limited by `max\_paths`

\* Number of scans with no attack paths

\* Path cutoff used

\* Maximum allowed paths



Default configuration:



```text

cutoff = 5

max\_paths = 100

```



\---



\## 5. Path-Length Metric



Path length can be measured as the number of graph edges in the path.



Example:



```text

Internet

&#x20;  ↓

EC2

&#x20;  ↓

IAM Role

&#x20;  ↓

IAM Policy

&#x20;  ↓

S3 Bucket

```



This path contains:



```text

4 edges

```



The configured cutoff of 5 allows paths up to five edges.



\---



\## 6. Bounded Search Metrics



The implementation limits graph traversal using:



```text

cutoff = 5

max\_paths = 100

```



The following values can be monitored:



| Metric         | Description                                |

| -------------- | ------------------------------------------ |

| Path cutoff    | Maximum number of edges in a path          |

| Maximum paths  | Maximum number of returned paths           |

| Paths returned | Number of paths actually returned          |

| Paths limited  | Whether the maximum path limit was reached |



A dedicated test verifies that the maximum path limit is respected.



\---



\## 7. API Performance Metrics



The following metrics should be measured for:



```text

GET /scans/{scan\_id}/attack-paths

```



\* Response time

\* HTTP status code

\* Number of graph nodes

\* Number of graph edges

\* Number of discovered paths

\* Number of paths limited by `max\_paths`



Response time should be recorded in milliseconds.



Production response-time values have not been established during local unit testing and should be measured during integration or deployment testing.



\---



\## 8. Collector Metrics



The collector can be monitored using:



\* Number of EC2 instances collected

\* Number of IAM roles collected

\* Number of resources skipped

\* Number of collection errors

\* Collection duration



Individual resource failures should not stop collection of other resources.



\---



\## 9. Test Metrics



Current Member 3 test results:



| Test Group            | Passed |

| --------------------- | -----: |

| Cloud collector tests |     14 |

| Attack-path tests     |      9 |

| Attack-path API test  |      1 |

| Member 3 tests        |     24 |



These values represent the tests currently implemented for the Member 3 changes.



The complete backend test suite should also be executed before the final GitHub push.



\---



\## 10. Correctness Metrics



The implementation should maintain the following correctness properties:



\* Duplicate relationships are removed.

\* Private security groups do not create `EXPOSES` relationships.

\* Unsupported relationships are not fabricated.

\* Attack-path search is bounded.

\* Finding severity remains associated with the correct resource.

\* Risk scores remain associated with the correct finding.

\* Scan ownership is enforced.

\* NetworkX implementation details are not exposed through the API.



\---



\## 11. Example Metrics



The following is an example only:



| Metric                  | Example |

| ----------------------- | ------: |

| Total graph resources   |       4 |

| Graph edges             |       3 |

| EC2 → IAM role edges    |       1 |

| IAM role → policy edges |       1 |

| Internet → EC2 edges    |       1 |

| Attack paths            |       0 |

| Longest path            |       0 |

| Path cutoff             |       5 |

| Maximum paths           |     100 |



The example values above should not be treated as production measurements.



\---



\## 12. Limitations



Current limitations include:



\* Complete normalized cloud relationship data is not persisted for every scan.

\* Static scans therefore do not generate unsupported relationships.

\* Live scan attack-path generation may use current cloud resource information.

\* Policy-to-S3 paths require explicit normalized relationship data.

\* Production API response-time metrics require deployment-level measurement.



These limitations prevent the system from making unsupported claims about cloud relationships or exploitability.



\---



\## 13. Future Phase 7 Monitoring



Future monitoring can add:



\* Average attack-path API response time

\* P95 response time

\* Maximum graph size

\* Average graph node count

\* Average graph edge count

\* Average number of attack paths

\* Maximum number of paths reached

\* Number of scans with zero attack paths

\* Number of skipped resources

\* Number of collector failures

\* API error rate



These measurements can be collected after integration and deployment testing.



