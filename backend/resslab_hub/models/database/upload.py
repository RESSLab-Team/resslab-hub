"""
What the uploader wrote last: one row per data-repo file, with the sha256 of the
content it loaded. A run skips every file whose hash did not change, and deletes
the rows of a file that left the repo (``resslab_hub.data.uploader.upload_all``).
"""

from sqlalchemy import Column, DateTime, String

from resslab_hub.utils.database import Base


class UploadedFile(Base):  # type: ignore
    __tablename__ = "uploaded_file"

    # "<upload type>/<file name>", e.g. "brace-displacement/B1.csv". The README
    # of a folder is "readme/<database>", since every folder has a README.md.
    # See upload_key() in the uploader.
    key = Column(String, primary_key=True)
    sha256 = Column(String(64), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False)
