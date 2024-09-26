# Convert PPTX pdf into Images for Text Extraction

Powerpoint presentations saved as PDFs present issues when trying to read the text.
This code extracts the PDFs from Object Store and extracts each page as a JPG image.

There are some pre-requisites in order for the PDF to Image to work. 

The JPG Images (each page) is sent to OCI Vision AI service to do "Text Extraction".

We then store that text as raw JSON into the Database. This can then be Vector Embedded for "Search" across all text in the Powerpoint presentation
