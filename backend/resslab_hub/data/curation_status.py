"""The review status of a row (#253), a column the Hub manages.

Every main table carries `data_curation_status`. A submission goes live as
`unverified` (the submission code stamps it, whatever the batch says), and a
curator's verification pull request changes it to `verified`. Contributors
never send it, so the validator does not require it from a contributed file.
"""

STATUS_COLUMN = "data_curation_status"
VERIFIED = "verified"
UNVERIFIED = "unverified"
ALLOWED = (VERIFIED, UNVERIFIED)
