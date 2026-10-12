# The DVC remote is private

The Singapore Open Data Licence allows redistributing the data with
attribution, so a public remote would be legal. We keep the remote private
anyway: nothing is redistributed, so there's no attribution to maintain on
stored copies, and anyone reproducing the project can re-run ingestion
against data.gov.sg directly. The bucket is shared across projects (see
the repo-level ADR-0001). The provider (Cloudflare R2 or AWS S3) is chosen in
step 1.
