"""Data models for validation results."""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConfidenceScoreRecord(BaseModel):
    """Typed representation of the confidence score agent output written to BigQuery."""

    mirakl_product_id: str = Field(description="Unique product identifier from Mirakl")
    status: str = Field(description="Processing status — must be 'validated'")
    confidence_score: float = Field(description="AI-assigned quality score from 0 to 100")
    validation_decision: str = Field(description="Final decision — 'Approve' or 'Reject'")
    ai_comment: str = Field(description="Point-by-point reasoning behind the score and decision")
    variant_group_code: str | None = Field(default=None, description="VGC code (style_number) grouping product variants")
    brand: str | None = Field(default=None, description="Product brand")
    title: str | None = Field(default=None, description="Product title")
    description: str | None = Field(default=None, description="Product description")
    size: str | None = Field(default=None, description="Product size variant")
    colour: str | None = Field(default=None, description="Product colour variant")
    seller: str | None = Field(default=None, description="Seller identifier from sources[0].provider_code")

    def to_bq_row(self) -> dict[str, Any]:
        """Return a flat dict ready for BigQuery insert_rows_json."""
        return {
            "mirakl_product_id": self.mirakl_product_id,
            "status":            self.status,
            "confidence_score":  self.confidence_score,
            "validation_decision": self.validation_decision,
            "ai_comment":        self.ai_comment,
            "variant_group_code": self.variant_group_code,
            "brand":             self.brand,
            "title":             self.title,
            "description":       self.description,
            "size":              self.size,
            "colour":            self.colour,
            "seller":            self.seller,
        }


class ValidationRecord(BaseModel):
    """Validation record to be stored in BigQuery."""

    product_details: dict[str, Any] = Field(
        description="Original product data from API"
    )
    image_validation: dict[str, Any] = Field(
        description="Image dimension validation results"
    )
    attribute_validation: dict[str, Any] = Field(
        description="Product attribute validation results"
    )

    def to_bq_row(self) -> dict[str, Any]:
        """Convert to flattened BigQuery row format."""
        # Extract product details
        product_id = self.product_details.get("id", "unknown")
        product_type = self.product_details.get("product_type", "unknown")
        product_attrs = self.product_details.get("product_attributes", {})
        images = self.product_details.get("images", [])
        
        # Determine overall validation status
        image_valid = self.image_validation.get("valid", False)
        attribute_valid = self.attribute_validation.get("valid", False)
        overall_valid = image_valid and attribute_valid
        
        # Build flattened row
        row = {
            # Core identifiers
            "product_id": product_id,
            "product_type": product_type,
            "validation_status": "PASS" if overall_valid else "FAIL",
            "validation_timestamp": datetime.utcnow().isoformat(),
            
            # Product attributes (flattened)
            "product_title": product_attrs.get("product_title"),
            "product_description": product_attrs.get("product_description"),
            "brand": product_attrs.get("brand"),
            "category": product_attrs.get("category"),
            "sku": product_attrs.get("sku"),
            "price": product_attrs.get("price"),
            "discount_percentage": product_attrs.get("discount_percentage"),
            "rating": product_attrs.get("rating"),
            "stock": product_attrs.get("stock"),
            "tags": json.dumps(product_attrs.get("tags", [])),
            "image_url": images[0].get("url") if images else None,
            
            # Image validation (flattened)
            "image_valid": image_valid,
            "image_width": self.image_validation.get("width"),
            "image_height": self.image_validation.get("height"),
            "image_min_required": self.image_validation.get("min_required"),
            "image_actual_dimensions": self.image_validation.get("actual"),
            "image_validation_message": self.image_validation.get("message") or self.image_validation.get("error"),
            
            # Attribute validation (flattened)
            "attribute_valid": attribute_valid,
            "attribute_status": self.attribute_validation.get("status"),
            "attribute_validation_message": self.attribute_validation.get("message"),
            "missing_attributes": json.dumps(self.attribute_validation.get("missing_attributes", [])),
            "empty_attributes": json.dumps(self.attribute_validation.get("empty_attributes", [])),
            "required_attributes": json.dumps(self.attribute_validation.get("required_attributes", [])),
        }
        
        # Add any additional product-specific attributes dynamically
        for key, value in product_attrs.items():
            if key not in row and value is not None:
                # Store additional attributes with 'attr_' prefix to avoid conflicts
                if isinstance(value, (dict, list)):
                    row[f"attr_{key}"] = json.dumps(value)
                else:
                    row[f"attr_{key}"] = value
        
        return row
