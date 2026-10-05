## Featured Products
Question 1: - Trace the feature. Explain how marking a product as featured in the admin interface causes the badge to appear in the storefront. Explain the files involved and the code logic. 

Q1 Answer: Claude modified products/models.py, templates/products/catalog.html, and templates/products/detail.html. When looping to display products, the templates check for if the is_featured value of the Product model is true or false, and displays the badge on the product if the value is true. 

Question 2 - How you verified it. Describe how you confirmed the feature works. Name the pages you checked in the browser.

Q2 Answer: I read the suggested code in real time before saying yes to Claude. In the browser, I checked the Catalog, products/seraphine/, products/soulsear-mark-i/, products/soulsear-mark-ii/ pages to make sure the badge was visible. I also looked at other product pages to check that the badge didn't always appear.

Question 3 - Judgement. Describe one challenge, unexpected result, or edge case you encountered. Explain what you did to troubleshoot it.

Q3 Answer: Claude tried to run makemigrations, migrations, and tests at the same time. I originally said yes, but realized I actually wanted to have Claude do each step one at a time. I cancelled the process and rewound to the previous state. I then ran the command again, but had Claude work step by step instead.

## Discount Coupons
Question 1 - One decision from grill me. Choose one /grill-me question that led to an important design decision. If you disagreed with the agent's recommendation, explain what it recommended, why you rejected that recommendation, what you chose instead, and how your choice affected the feature. If you did not disagree with any recommendation, choose a question that was confusing. Explain what you did not understand, the follow-up question(s) you asked, and how you ultimately decided.

Q1 Answer: A question that led to an important design decision was: "Question 6: What decides when a code is valid". Claude's original recommendation was Option 1, which outlined a discount code would expire at datetime, and a blank value would mean the code never expires. I asked Claude which option would be closer to the prompt: "the plan is seasonal promotions." With the newly offer context for what I was looking for, Claude changed its recommendation to a modified version of Option 2, which outlined a start_at and expires_at system instead. The modification made "starts_at" default to "now". This allowed promotions to be secheduled in advance.

Question 2 - The change. Explain the change you made after reviewing the feature. Describe your original choice, what the browser showed you, why you wanted to change it, and how the fix works. If any existing test failed during your build, name it and say what you did about it.

Q2 Answer: While using the browser to check the feature's functionality, I noticed a visual issue in the discount edit page of the back office. The list was horizontal rather than vertical, and the text of each product was wrapping too often making it barely readable. No tests failed because the code worked. However, it was difficult for a user to read and select which items the discount code should apply to. I brought up the visual issue to Claude. I outlined what I believed the problem was, and Claude looked into the code. Claude found the issue in products/forms.py and suggested a potential fix. I had Claude make the fix, and I reloaded the discount code edit page to check if it worked. The fix worked perfectly and the list was now readable.

## Product Images
Question 1 - One decision from grill me. Choose one /grill-me question that led to an important design decision. If you disagreed with the agent's recommendation, explain what it recommended, why you rejected that recommendation, what you chose instead, and how your choice affected the feature. If you did not disagree with any recommendation, choose a question that was confusing. Explain what you did not understand, the follow-up question(s) you asked, and how you ultimately decided.

Q1 Answer: I didn't reject any of the recommendation. We were on the same page for the entire grill-me. However, my expansion on Question 6 led to Question 7, which led to an important design decision. Question 6 was about error messages on file upload. I added that we need a default error message in case none of the others fit the error.

Question 2 - Find the upload code. Find the ImageField the agent added to the Product model. Copy that line into your answer and include the filename and line number. Explain what the upload_to value does.
Find the <form> used to upload a product image. Copy the opening <form> tag into your answer and include the filename and line number. Explain why enctype is needed for a file upload.

Q2 Answer:
- The ImageFields added was: "image = models.ImageField(upload_to=product_image_path, max_length=255, blank=True, editable=False)" and "image_original = models.ImageField(upload_to=product_original_path, max_length=255, blank=True, editable=False)" located in products/models.py on lines 86-91. The upload_to value is a function which is called each time a file is saved, and it returns the name of the file. 
- The form: <form method="post" enctype="multipart/form-data" class="mt-2 space-y-4"> is in templates/products/manage_product_form.html on line 13. It is needed because this is the part that send the file along with its name.

Question 3 - Follow the upload process. Your invented product's image is stored somewhere on disk and served from some URL. Follow the image for the product you created through the application and write: 1. The path where the image file is stored on disk. 2. The value stored in the database for that image. 3. The URL the browser requests to display it.

Q3 Answer: The path of my image is: media\products\syncrest-mark-ii-6bd6b84b.webp. The value stored in the database is: "products/syncrest-mark-ii-6bd6b84b.webp". The URL that the browser requests to display the image is: http://127.0.0.1:8000/media/products/syncrest-mark-ii-6bd6b84b.webp. All three have "products/syncrest-mark-ii-6bd6b84b.webp", but the directories of each are different.