"""
MongoDB holds the raw uploaded bytes (base64/text) and free-form upload
metadata -- the stuff that doesn't have a fixed schema. Postgres holds the
chunked, embedded, queryable representation. This split is the SQL+NoSQL
half of the stack: structured/vector data in Postgres, schema-flexible raw
artifacts in Mongo.
"""
from datetime import datetime

from pymongo import MongoClient

from app.config import settings

_client = MongoClient(settings.mongo_url)
_db = _client[settings.mongo_db_name]

raw_documents = _db["raw_documents"]  # {_id, vendor_id, filename, content_type, raw_text, uploaded_at, tags}


def store_raw_document(vendor_id: int | None, filename: str, content_type: str, raw_text: str, tags: dict) -> str:
    doc = {
        "vendor_id": vendor_id,
        "filename": filename,
        "content_type": content_type,
        "raw_text": raw_text,
        "uploaded_at": datetime.utcnow(),
        "tags": tags,
    }
    result = raw_documents.insert_one(doc)
    return str(result.inserted_id)


def get_raw_document(doc_id: str) -> dict | None:
    from bson import ObjectId

    return raw_documents.find_one({"_id": ObjectId(doc_id)})
