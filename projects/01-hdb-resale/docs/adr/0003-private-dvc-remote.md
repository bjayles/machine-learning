# The DVC remote is private

The Singapore Open Data Licence allows redistributing the data with
attribution, so a public remote would be legal. We keep the remote private
anyway: nothing is redistributed, so there's no attribution to maintain on
stored copies, and anyone reproducing the project can re-run ingestion
against data.gov.sg directly. The bucket is shared across projects (see
the repo-level ADR-0001). The provider, chosen in step 1, is AWS S3 in a
dedicated workloads account (repo ADR-0002).
