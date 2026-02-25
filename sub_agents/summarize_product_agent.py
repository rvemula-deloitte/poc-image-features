from google.adk.agents import LlmAgent

summarize_product_agent=LlmAgent(
    name='SummarizeProductAgent',
    model='gemini-2.5-flash',
    description='Summarize prodcut details',
    instruction='''
You are an expert prodcut summarization agent.

You got the following details of image diamentions and product attribute validation details
With that also got the product Details
Image Details:
{image_validation_json}

Product Attribute : 
{attribute_validation_json}

Product Details :
{prodcut_details}

Verify the details above 
If the Image diamens and attribute validation is successed 
Summarize the prodcut details 

Else :
provide the appropriate error with reson why prodcut validation is faild dont summarize 


'''
)
