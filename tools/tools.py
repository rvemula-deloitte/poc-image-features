import requests
from io import BytesIO
from PIL import Image

def validate_image(image_url:str)->dict:
    """ 
    Download an image and validate image dimensions
    Args:
        image_url (str): URL of the image to download
    
    Returns:
        dict: Validation result with status and details
    """

    min_width = 1920
    min_height = 1080
    
    try:
        response = requests.get(image_url, timeout=10)
        
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))

        width, height = img.size

        is_valid = width >= min_width and height >= min_height

        result = {
                'valid': is_valid,
                'width': width,
                'height': height,
                'min_required': f"{min_width}×{min_height}",
                'actual': f"{width}×{height}",
                'message': 'Image meets requirements' if is_valid else f'Image too small: {width}×{height} (minimum {min_width}×{min_height})'
            }
        
        return result

    except requests.exceptions.RequestException as e:
        return {'valid': False, 'error': f'Download failed: {str(e)}'}
    
    except Exception as e:
        return {'valid': False, 'error': f'Validation failed: {str(e)}'}





# image_url = 'https://fastly.picsum.photos/id/4/5000/3333.jpg?hmac=ghf06FdmgiD0-G4c9DdNM8RnBIN7BO0-ZGEw47khHP4'

# print(validate_image(image_url))



required_attributes_by_product_type = {
  "_common_required_for_all": [
    "brand",
    "product_title",
    "product_description",
    "price"
  ],

  "apparel_accessories": [
    "size",
    "size_system",
    "color",
    "material_composition",
    "fit",
    "care_instructions",
    "gender_age_group"
  ],

  "footwear": [
    "shoe_size",
    "size_system",
    "width",
    "color",
    "upper_material",
    "outsole_material",
    "closure_type",
    "intended_use_activity"
  ],

  "beauty_personal_care": [
    "net_volume_or_weight",
    "product_form",
    "skin_hair_type",
    "benefit_concern",
    "ingredients",
    "usage_instructions",
    "warnings"
  ],

  "health_wellness_otc_supplements": [
    "count_or_net_weight",
    "active_ingredients",
    "dosage_strength",
    "servings_per_container",
    "directions",
    "warnings",
    "allergen_statement"
  ],

  "grocery_food_beverage": [
    "net_weight_or_volume",
    "ingredients",
    "allergens",
    "nutrition_facts",
    "dietary_claims",
    "storage_instructions",
    "expiration_or_best_by_date"
  ],

  "baby_kids": [
    "age_range",
    "size_or_weight_range",
    "material",
    "care_cleaning_instructions",
    "safety_warnings",
    "certifications_compliance"
  ],

  "toys_games": [
    "age_grading",
    "pieces_count",
    "material",
    "dimensions",
    "safety_warnings",
    "certifications_compliance"
  ],

  "electronics_consumer": [
    "model_number_mpn",
    "key_specs",
    "compatibility",
    "connectivity",
    "included_accessories",
    "warranty"
  ],

  "computers_peripherals": [
    "model_number_mpn",
    "compatibility",
    "interface_connection_type",
    "key_specs",
    "dimensions",
    "warranty"
  ],

  "mobile_phones_accessories": [
    "device_compatibility",
    "connector_type",
    "key_specs",
    "color",
    "included_items",
    "warranty"
  ],

  "home_appliances": [
    "capacity",
    "dimensions",
    "installation_requirements",
    "power_requirements",
    "key_features_programs",
    "warranty"
  ],

  "home_kitchen": [
    "material",
    "dimensions_or_capacity",
    "care_cleaning_instructions",
    "set_contents_piece_count",
    "compatibility_use_limits",
    "safety_warnings"
  ],

  "furniture": [
    "dimensions",
    "material",
    "color_finish",
    "load_capacity",
    "assembly_required",
    "care_instructions"
  ],

  "home_improvement_hardware": [
    "material_finish",
    "size_measurements",
    "compatibility_standards",
    "intended_use_location",
    "included_parts",
    "installation_requirements"
  ],

  "tools_diy": [
    "power_source",
    "power_specs_voltage_amp_or_watt",
    "performance_specs",
    "compatibility_system_platform",
    "included_accessories",
    "warranty"
  ],

  "garden_outdoor_living": [
    "material",
    "dimensions",
    "weather_uv_resistance",
    "power_source_or_fuel_type",
    "capacity_coverage",
    "assembly_required"
  ],

  "sports_fitness": [
    "size_fit",
    "material",
    "sport_activity_type",
    "skill_level_use_case",
    "safety_certifications",
    "care_instructions"
  ],

  "automotive_parts_accessories": [
    "vehicle_fitment",
    "part_number",
    "oem_aftermarket_flag",
    "position",
    "installation_notes",
    "warranty"
  ],

  "pet_supplies": [
    "pet_type",
    "life_stage_or_size",
    "material_or_ingredients",
    "dimensions_or_capacity",
    "usage_instructions",
    "warnings"
  ],

  "office_supplies": [
    "size_format",
    "quantity_count",
    "color",
    "material",
    "compatibility",
    "pack_contents"
  ],

  "arts_crafts_sewing": [
    "material",
    "color",
    "quantity_length_weight",
    "compatibility",
    "safety_non_toxic_flag",
    "usage_care_instructions"
  ],

  "books_music_media": [
    "format",
    "creator_author_artist",
    "publisher_label",
    "release_date",
    "language",
    "identifier_isbn_upc"
  ],

  "video_games": [
    "platform",
    "format_physical_digital",
    "edition",
    "region",
    "age_rating",
    "players_online_local"
  ],

  "jewelry_watches": [
    "material",
    "size_length",
    "stone_details",
    "closure_clasp_type",
    "care_instructions",
    "warranty"
  ],

  "luggage_travel": [
    "dimensions",
    "capacity_liters",
    "weight",
    "material",
    "wheel_handle_features",
    "lock_type"
  ],

  "industrial_b2b_supplies": [
    "specifications_standards",
    "material_grade",
    "dimensions_tolerances",
    "operating_limits",
    "compliance_certifications",
    "traceability_lot_serial"
  ]
}




def Attribute_validation(product_type: str, attribution_dict: dict) -> dict:
    """
    Verify the attributes based on the product type.
    Validates both common required attributes and product-type-specific attributes.
    
    Args:
        product_type: Name of the product type (e.g., 'apparel_accessories', 'footwear')
        attribution_dict: Dictionary containing product attributes to validate
        
    Returns:
        dict: Validation result with status and details.
    """
    common_attributes = required_attributes_by_product_type.get("_common_required_for_all", [])
    
    # Check if product type exists in configuration
    if product_type not in required_attributes_by_product_type:
       
        all_required_attributes = common_attributes
    
    
    else:
        product_specific_attributes = required_attributes_by_product_type[product_type]
    
        # Combine common and product-specific attributes
        all_required_attributes = common_attributes + product_specific_attributes
    
    missing_attributes = []
    empty_attributes = []
    
    # Check for missing and empty attributes
    for attribute in all_required_attributes:
        if attribute not in attribution_dict:
            missing_attributes.append(attribute)
        elif attribution_dict[attribute] is None or attribution_dict[attribute] == "":
            empty_attributes.append(attribute)
    
    # Determine validation status
    if missing_attributes or empty_attributes:
        return {
            "status": "failed",
            "valid": False,
            "message": "Validation failed: Missing or empty required attributes",
            "missing_attributes": missing_attributes,
            "empty_attributes": empty_attributes,
            "required_attributes": all_required_attributes,
            "provided_attributes": list(attribution_dict.keys())
        }
    else:
        return {
            "status": "success",
            "valid": True,
            "message": "All required attributes are present and valid",
            "missing_attributes": [],
            "empty_attributes": [],
            "required_attributes": all_required_attributes,
            "provided_attributes": list(attribution_dict.keys())
        }



from typing import Dict, Any



def fetch_product_from_api(product_id: str) -> Dict[str, Any]:
    """
    Calls DummyJSON:
      GET https://dummyjson.com/products/{product_id}
 
    Returns standardized shape for your pipeline:
    {
      "id": "123",
      "product_type": "dress",
      "attributes": {...},
      "images": [{"url":"..."}, ...]
    }
    """
    url = f"https://dummyjson.com/products/{product_id}"
    resp = requests.get(url, headers={"Accept": "application/json"}, timeout=30)
    resp.raise_for_status()
    p: Dict[str, Any] = resp.json()
 
    # DummyJSON doesn't provide apparel-specific attributes like sleeve_length/size/fabric_type reliably.
    # Keep a consistent contract and pass through what DummyJSON *does* provide as attributes.
    product_type = (p.get("category") or "unknown").lower()
 
    attributes = {
        # Pass-through commonly present DummyJSON fields
        "product_title": p.get("title"),
        "product_description": p.get("description"),
        "brand": p.get("brand"),
        "category": p.get("category"),
        "sku": p.get("sku"),
        "price": p.get("price"),
        "discount_percentage": p.get("discountPercentage"),
        "rating": p.get("rating"),
        "stock": p.get("stock"),
        "tags": p.get("tags"),
 
        # Your “required attributes” keys (will often be None with DummyJSON)
        "color": None,
        "size": None,
        "fabric_type": None,
        "sleeve_length": None,
    }
 
    images = [{"url": u} for u in (p.get("images") or []) if isinstance(u, str) and u.strip()]
 
    return {
        "id": str(p.get("id") or product_id),
        "product_type": product_type,
        "product_attributes": attributes,
        "images": images,
    }

