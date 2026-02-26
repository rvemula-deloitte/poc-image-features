import requests
from io import BytesIO
from PIL import Image
from typing import Dict, Any, List
from google.adk.tools import FunctionTool


def validate_image(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """ 
    Download and validate image dimensions for multiple products sequentially.
    
    Args:
        products: List of product dictionaries containing image URLs.
                  Each product should have 'id' or 'mirakl_product_id' and 'images' list.
    
    Returns:
        dict: Validation results with per-product results and summary
    """
    min_width = 1920
    min_height = 1080
    results = []
    
    # Process each product sequentially
    for product in products:
        product_id = product.get('id') or product.get('mirakl_product_id') or 'unknown'
        
        # Extract image URL from product
        images = product.get('images', [])
        if not images:
            # Try alternate structure
            data = product.get('data', {})
            main_image = data.get('main_image', {})
            image_url = main_image.get('original_url') or main_image.get('source')
        else:
            image_url = images[0].get('url') if images else None
        
        if not image_url:
            results.append({
                'product_id': product_id,
                'image_validation': {'valid': False, 'error': 'No image URL found'}
            })
            continue
        
        # Validate the image
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            width, height = img.size
            
            is_valid = width >= min_width and height >= min_height
            
            validation_result = {
                'valid': is_valid,
                'width': width,
                'height': height,
                'min_required': f"{min_width}×{min_height}",
                'actual': f"{width}×{height}",
                'message': 'Image meets requirements' if is_valid else f'Image too small: {width}×{height} (minimum {min_width}×{min_height})'
            }
            
            results.append({
                'product_id': product_id,
                'image_url': image_url,
                'image_validation': validation_result
            })
            
        except requests.exceptions.RequestException as e:
            results.append({
                'product_id': product_id,
                'image_url': image_url,
                'image_validation': {'valid': False, 'error': f'Download failed: {str(e)}'}
            })
        except Exception as e:
            results.append({
                'product_id': product_id,
                'image_url': image_url,
                'image_validation': {'valid': False, 'error': f'Validation failed: {str(e)}'}
            })
    
    # Calculate summary
    valid_count = sum(1 for r in results if r.get('image_validation', {}).get('valid', False))
    
    return {
        'results': results,
        'summary': {
            'total': len(results),
            'valid': valid_count,
            'failed': len(results) - valid_count
        }
    }





# image_url = 'https://fastly.picsum.photos/id/4/5000/3333.jpg?hmac=ghf06FdmgiD0-G4c9DdNM8RnBIN7BO0-ZGEw47khHP4'

# print(validate_image(image_url))



required_attributes_by_product_type = {
    "_common_required_for_all": [
        "brand",
        "title",
        "product_category",
        "main_image"
    ],
    "5_8_1_99999_125_1035": [
        "care",
        "origin",
        "feature_1",
        "feature_2",
        "color_family",
        "style_number",
        "display_color",
        "choking_hazard",
        "fabric_material",
        "meta_description",
        "style_description",
        "perishable_indicator",
        "nrf_size-5_8_1_99999_125_1035"
    ],
    "3_14_63": [
        "care",
        "origin",
        "prop_65",
        "Priority",
        "feature_1",
        "feature_2",
        "feature_3",
        "is_ltl_item",
        "color_family",
        "containsPFAS",
        "room-3_14_63",
        "style_number",
        "display_color",
        "choking_hazard",
        "fabric_material",
        "meta_description",
        "nrf_size-3_14_63",
        "style_description",
        "perishable_indicator",
        "recommended_usage-3_14_63"
    ],
    "33_106_1479": [
        "care",
        "origin",
        "feature_1",
        "feature_2",
        "color_family",
        "style_number",
        "display_color",
        "choking_hazard",
        "fabric_material",
        "meta_description",
        "style_description",
        "nrf_size-33_106_1479",
        "perishable_indicator",
        "recommended_usage-33_106_1479"
    ]
}





def Attribute_validation(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verify the attributes based on the product type for multiple products sequentially.
    Validates both common required attributes and product-type-specific attributes.
    
    Args:
        products: List of product dictionaries.
                  Each product should have 'id', 'product_type', and 'product_attributes'.
        
    Returns:
        dict: Validation results with per-product results and summary
    """
    results = []
    common_attributes = required_attributes_by_product_type.get("_common_required_for_all", [])
    
    # Process each product sequentially
    for product in products:
        product_id = product.get('id') or product.get('mirakl_product_id') or 'unknown'
        
        # Extract product type and attributes
        product_type = product.get('product_type') or product.get('data', {}).get('product_category')
        attribution_dict = product.get('product_attributes') or product.get('data', {})
        
        if not product_type:
            results.append({
                'product_id': product_id,
                'attribute_validation': {
                    'status': 'failed',
                    'valid': False,
                    'error': 'No product type found'
                }
            })
            continue
        
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
            validation_result = {
                "status": "failed",
                "valid": False,
                "message": "Validation failed: Missing or empty required attributes",
                "missing_attributes": missing_attributes,
                "empty_attributes": empty_attributes,
                "required_attributes": all_required_attributes,
                "provided_attributes": list(attribution_dict.keys())
            }
        else:
            validation_result = {
                "status": "success",
                "valid": True,
                "message": "All required attributes are present and valid",
                "missing_attributes": [],
                "empty_attributes": [],
                "required_attributes": all_required_attributes,
                "provided_attributes": list(attribution_dict.keys())
            }
        
        results.append({
            'product_id': product_id,
            'product_type': product_type,
            'attribute_validation': validation_result
        })
    
    # Calculate summary
    valid_count = sum(1 for r in results if r.get('attribute_validation', {}).get('valid', False))
    
    return {
        'results': results,
        'summary': {
            'total': len(results),
            'valid': valid_count,
            'failed': len(results) - valid_count
        }
    }





from typing import Dict, Any



def fetch_products_from_mirakl(updated_since: str = None, updated_to: str = None, product_sku: str = None) -> List[Dict[str, Any]]:
    """
    Fetch products from Mirakl API.
    Args:
        updated_since (str): ISO 8601 date string (e.g., "2026-02-15T09:31:48Z")
        updated_to (str): ISO 8601 date string (e.g., "2026-02-23T16:51:48Z")
        product_sku (str): Optional product SKU filter (e.g., "4135850671899")
    Returns:
        List[Dict[str, Any]]: List of product data
    """
    url = "https://kohlsus-dev.mirakl.net/api/mcm/products/export"
    params = {}
    if updated_since:
        params['updated_since'] = updated_since
    if updated_to:
        params['updated_to'] = updated_to
    if product_sku:
        params['product_sku'] = product_sku

    headers = {
        'Authorization': '504c4fc7-6402-48b3-bc29-34d82e964918',
        'Accept': 'application/json'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        products = response.json()
        
        formatted_products = []
        for p in products:
            # Extract relevant fields
            data = p.get('data', {})
            product_sku = p.get('product_sku')
            
            # Extract image URL
            main_image = data.get('main_image', {})
            image_url = main_image.get('original_url') or main_image.get('source')
            
            product_info = {
                "id": p.get('mirakl_product_id'),
                "product_type": data.get('product_category'), # Using category as type
                "product_sku": product_sku,
                "product_attributes": {
                    "product_title": data.get('title'),
                    "brand": data.get('brand'),
                    "sku": product_sku,
                    # Add other attributes as needed from data
                    **data # Include all other data fields
                },
                "images": [{"url": image_url}] if image_url else []
            }
            formatted_products.append(product_info)
            
        return formatted_products

    except requests.exceptions.RequestException as e:
        print(f"Error fetching products: {e}")
        return []

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


# Create ADK FunctionTool wrappers for proper schema generation
validate_image_tool = FunctionTool(func=validate_image)
validate_attributes_tool = FunctionTool(func=Attribute_validation)
fetch_products_tool = FunctionTool(func=fetch_products_from_mirakl)
fetch_product_tool = FunctionTool(func=fetch_product_from_api)
