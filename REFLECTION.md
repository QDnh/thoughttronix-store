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