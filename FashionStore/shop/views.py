from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.db.models import Count
from django.urls import reverse
from django.http import HttpResponse, JsonResponse

# Chatbot AI imports
import json
import os
import random
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt

# AI/NLP Libraries
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
import spacy

# Assuming your models are in .models
from .models import Category, SubCategory, Product, CustomUser
from .forms import SignupForm, LoginForm, CategoryForm, ProductForm

# Load spaCy model globally (only once)
nlp = None
try:
    nlp = spacy.load("en_core_web_sm")
    print("spaCy model 'en_core_web_sm' loaded successfully.")
except OSError:
    print("spaCy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm' in your terminal.")
    # Fallback if spacy model is not found, product extraction won't use tokenization fully
    pass # Continue without nlp, but extraction might be less precise

# --- Chatbot AI Model Training (Global Scope) ---
INTENTS_DATA_PATH = os.path.join(settings.BASE_DIR, 'shop', 'chatbot_intents.json')
intents = []
vectorizer = None
clf = None

try:
    with open(INTENTS_DATA_PATH, 'r', encoding='utf-8') as f:
        intents = json.load(f)
    print(f"Chatbot intents loaded successfully from {INTENTS_DATA_PATH}. {len(intents)} intents found.")

    training_sentences = []
    training_labels = []
    for intent in intents:
        for pattern in intent['patterns']:
            training_sentences.append(pattern.lower())
            training_labels.append(intent['tag'])

    if training_sentences:
        vectorizer = TfidfVectorizer()
        X_train = vectorizer.fit_transform(training_sentences)
        clf = LinearSVC()
        clf.fit(X_train, training_labels)
        print("Chatbot intent model trained successfully using TF-IDF and LinearSVC.")
    else:
        print("WARNING: No training sentences found in intents data. Intent recognition will not work.")

except FileNotFoundError:
    print(f"ERROR: chatbot_intents.json not found at {INTENTS_DATA_PATH}. Chatbot intent recognition will be limited.")
    intents = []
except json.JSONDecodeError as e:
    print(f"ERROR: Could not decode JSON from {INTENTS_DATA_PATH}. Check file format. Error: {e}")
    intents = []
except Exception as e:
    print(f"ERROR: An unexpected error occurred during chatbot model loading/training: {e}")
    import traceback
    traceback.print_exc()

# --- Chatbot Logic Helper Function ---
def _get_chatbot_response_logic(user_message_str):
    user_message_lower = user_message_str.lower().strip()

    predicted_tag = "fallback"
    # Adjust this threshold based on testing. A slightly negative value often works for LinearSVC
    # if you want to be somewhat confident, but not overly strict. 0.0 might be better for "positive" classification.
    # For a multi-class classifier like LinearSVC, the decision_function returns scores relative to decision boundaries.
    # A score of 0 indicates the message is on the decision boundary. Positive scores are on one side, negative on the other.
    # For a multi-class setup, it's about the largest score.
    # A common approach is to look at the *difference* between the top two scores, or just take the top one.
    # Let's start with a simpler approach based on whether it's above a certain confidence level
    # or if the model was not loaded.
    confidence_threshold = 0.1 # A small positive threshold implies "some" confidence

    if clf and vectorizer:
        user_message_vectorized = vectorizer.transform([user_message_lower])
        # decision_function gives scores for each class. The class with the highest score is the predicted one.
        # For multi-class, it often provides (n_samples, n_classes) array of distances to hyperplanes.
        scores = clf.decision_function(user_message_vectorized)[0]
        max_score_index = scores.argmax()
        highest_confidence_score = scores[max_score_index]
        potential_tag = clf.classes_[max_score_index]

        print(f"DEBUG: User message: '{user_message_lower}'")
        print(f"DEBUG: Potential tag: {potential_tag}, Highest Confidence Score: {highest_confidence_score:.2f}")

        # You might need to experiment with `highest_confidence_score`
        # If it's the highest score among all, it's the prediction.
        # The threshold helps filter out very weak predictions that might be better handled by fallback.
        if highest_confidence_score > confidence_threshold:
            predicted_tag = potential_tag
        else:
            print(f"DEBUG: Highest confidence score {highest_confidence_score:.2f} is below threshold {confidence_threshold}, falling back.")
            predicted_tag = "fallback"
    else:
        print("WARNING: Chatbot model not loaded/trained. Falling back to simple keyword matching for basic intents.")
        # This basic keyword matching should only be a very simple fallback if ML fails completely.
        # The goal is for the ML model to handle almost everything.
        if any(kw in user_message_lower for kw in ["hi", "hello", "hey", "greetings"]):
            predicted_tag = "greeting"
        elif any(kw in user_message_lower for kw in ["bye", "goodbye", "see you", "farewell"]):
            predicted_tag = "goodbye"
        elif any(kw in user_message_lower for kw in ["thank you", "thanks", "appreciate"]):
            predicted_tag = "thanks"
        elif any(kw in user_message_lower for kw in ["who are you", "what are you", "are you ai"]):
            predicted_tag = "identity"
        elif any(kw in user_message_lower for kw in ["how can i pay", "payment methods"]):
            predicted_tag = "payment_methods"
        elif any(kw in user_message_lower for kw in ["shipping time", "delivery time"]):
            predicted_tag = "shipping_time"
        elif any(kw in user_message_lower for kw in ["return policy", "returns", "refund"]):
            predicted_tag = "return_policy"
        elif any(kw in user_message_lower for kw in ["international shipping", "ship internationally"]):
            predicted_tag = "international_shipping"
        elif any(kw in user_message_lower for kw in ["track my order", "order status"]):
            predicted_tag = "track_order"
        elif any(kw in user_message_lower for kw in ["contact support", "customer service"]):
            predicted_tag = "contact_support"
        elif any(kw in user_message_lower for kw in ["change order", "cancel order"]):
            predicted_tag = "change_cancel_order"
        elif any(kw in user_message_lower for kw in ["complaint", "issue with order"]):
            predicted_tag = "register_complaint"
        elif any(kw in user_message_lower for kw in ["rate", "review", "feedback"]):
            predicted_tag = "rate_review"
        elif any(kw in user_message_lower for kw in ["suggestions", "idea for improvement"]):
            predicted_tag = "suggestions"
        elif any(kw in user_message_lower for kw in ["about us", "who is eterna"]):
            predicted_tag = "about_us"
        elif any(kw in user_message_lower for kw in ["browse products", "show me products", "what do you sell"]):
            predicted_tag = "browse_products"
        elif any(kw in user_message_lower for kw in ["find a product", "search for an item", "looking for", "show me"]):
            predicted_tag = "product_search_query"
        elif any(kw in user_message_lower for kw in ["recommend products", "suggest products"]):
            predicted_tag = "product_recommendations"
        elif any(kw in user_message_lower for kw in ["product information", "details about product"]):
            predicted_tag = "product_info"
        elif any(kw in user_message_lower for kw in ["is it in stock", "check stock"]):
            predicted_tag = "check_stock"
        elif any(kw in user_message_lower for kw in ["complementary products", "what else goes with this"]):
            predicted_tag = "upsell_cross_sell"
        elif any(kw in user_message_lower for kw in ["promotions", "deals", "discounts", "sales"]):
            predicted_tag = "promotions"
        elif any(kw in user_message_lower for kw in ["size guide", "what's my size"]):
            predicted_tag = "size_guide"
        elif any(kw in user_message_lower for kw in ["cart assistance", "my cart", "checkout issues"]):
            predicted_tag = "cart_assistance"
        elif any(kw in user_message_lower for kw in ["add to cart", "buy item", "how to purchase"]):
            predicted_tag = "add_to_cart_instruction"
        elif any(kw in user_message_lower for kw in ["payment problem", "checkout help"]):
            predicted_tag = "payment_gateway_help"
        elif any(kw in user_message_lower for kw in ["shipping cost", "delivery estimates"]):
            predicted_tag = "shipping_cost"
        elif any(kw in user_message_lower for kw in ["lead generation", "contact me", "get updates"]):
            predicted_tag = "lead_generation"
        elif any(kw in user_message_lower for kw in ["create account", "sign up", "register"]):
            predicted_tag = "create_account"
        elif any(kw in user_message_lower for kw in ["checkout as guest", "guest checkout"]):
            predicted_tag = "guest_checkout"
        elif any(kw in user_message_lower for kw in ["reset password", "forgot password"]):
            predicted_tag = "reset_password"
        elif any(kw in user_message_lower for kw in ["digital receipt", "invoice", "get receipt"]):
            predicted_tag = "digital_receipts"
        elif any(kw in user_message_lower for kw in ["meaning of life", "philosophy", "purpose of existence"]):
            predicted_tag = "philosophical_query"
        # If no specific keyword match and ML model failed, it remains fallback.


    # --- Product Search and Entity Extraction (if predicted_tag is product_search_query) ---
    if predicted_tag == "product_search_query":
        # Product extraction logic: Use spaCy if available, otherwise simple keyword checks
        product_item_type = None
        color = None
        size = None
        main_category_preference = None
        search_query_term = user_message_lower # Used as a fallback if no specific entities are extracted

        # Use spaCy for more robust extraction if nlp model is loaded
        if nlp:
            doc = nlp(user_message_lower)
            # Gender/Main Category extraction
            if any(keyword in user_message_lower for keyword in ["women's wear", "womens wear", "ladies wear", "women", "ladies", "female"]):
                main_category_preference = "women_clothing"
            elif any(keyword in user_message_lower for keyword in ["men's wear", "mens wear", "gent's wear", "gents wear", "men", "gents", "male"]):
                main_category_preference = "men_clothing"
            elif any(keyword in user_message_lower for keyword in ["kid's wear", "kids wear", "children's wear", "kids", "children", "boys", "girls"]):
                main_category_preference = "kid_clothing"
            elif any(keyword in user_message_lower for keyword in ["shoes", "shoe", "footwear", "sneakers", "boots"]):
                main_category_preference = "shoes"
            elif any(keyword in user_message_lower for keyword in ["bags", "bag", "backpacks", "purse", "handbag"]):
                main_category_preference = "bags"
            elif any(keyword in user_message_lower for keyword in ["accessories", "accessory", "jewellery", "jewelry", "watches", "earrings", "necklace", "ring", "bracelet", "belt"]):
                main_category_preference = "accessories"


            product_type_keywords = {
                "dresses": "dress", "dress": "dress", "gown": "dress",
                "t-shirts": "t-shirt", "tshirt": "t-shirt", "tee": "t-shirt",
                "pants": "pant", "jeans": "jeans", "trouser": "pant",
                "shirts": "shirt", "shirt": "shirt",
                "top": "top", "tops": "top",
                "jackets": "jacket", "jacket": "jacket", "coat": "jacket",
                "skirts": "skirt", "skirt": "skirt",
                "saree": "saree", "sarees": "saree", "sari": "saree",
                "hoodie": "hoodie", "sweatshirt": "sweatshirt",
                "shorts": "shorts", "leggings": "leggings", "trousers": "trousers",
            }

            for token in doc:
                # Prioritize exact matches, then lemma matches
                if token.text in product_type_keywords:
                    product_item_type = product_type_keywords[token.text]
                    break
                elif token.lemma_ in product_type_keywords:
                    product_item_type = product_type_keywords[token.lemma_]
                    break
                # Consider dependency parsing if more advanced rules are needed, e.g., "red shirt" where "shirt" is the object.
                # if token.dep_ == 'dobj' and token.pos_ == 'NOUN' and token.text in product_type_keywords:
                #     product_item_type = product_type_keywords[token.text]
                #     break

            colors = ["red", "blue", "green", "black", "white", "pink", "yellow", "orange", "purple", "brown", "grey",
                      "silver", "gold"]
            for token in doc:
                if token.text in colors:
                    color = token.text
                    break

            size_mapping = {
                "xs": "XS", "extra small": "XS",
                "s": "S", "small": "S",
                "m": "M", "medium": "M",
                "l": "L", "large": "L",
                "xl": "XL", "x-large": "XL", "extra large": "XL",
                "xxl": "XXL", "xx-large": "XXL",
            }
            for token in doc:
                normalized_token = token.text.lower().replace('-', ' ')
                if normalized_token in size_mapping:
                    size = size_mapping[normalized_token]
                    break
        else: # Fallback to simple keyword search if spaCy is not loaded
            # Re-implement simple keyword checks for product details
            if any(keyword in user_message_lower for keyword in ["shoes", "shoe", "footwear", "sneakers", "boots"]):
                main_category_preference = "shoes"
            # ... (add other main_category_preference checks here as in your previous version)
            elif any(keyword in user_message_lower for keyword in ["bags", "bag", "backpacks", "purse", "handbag"]):
                main_category_preference = "bags"
            elif any(keyword in user_message_lower for keyword in ["accessories", "accessory", "jewellery", "jewelry", "watches", "earrings", "necklace", "ring", "bracelet", "belt"]):
                main_category_preference = "accessories"
            elif any(keyword in user_message_lower for keyword in ["women's wear", "womens wear", "ladies wear", "women", "ladies", "female", "dresses", "skirts", "tops"]):
                main_category_preference = "women_clothing"
            elif any(keyword in user_message_lower for keyword in ["men's wear", "mens wear", "gent's wear", "gents wear", "men", "gents", "male", "shirts", "pants"]):
                main_category_preference = "men_clothing"
            elif any(keyword in user_message_lower for keyword in ["kid's wear", "kids wear", "children's wear", "kids", "children", "boys", "girls"]):
                main_category_preference = "kid_clothing"

            product_type_keywords = {
                "dresses": "dress", "dress": "dress", "gown": "dress",
                "t-shirts": "t-shirt", "tshirt": "t-shirt", "tee": "t-shirt",
                "pants": "pant", "jeans": "jeans", "trouser": "pant",
                "shirts": "shirt", "shirt": "shirt",
                "top": "top", "tops": "top",
                "jackets": "jacket", "jacket": "jacket", "coat": "jacket",
                "skirts": "skirt", "skirt": "skirt",
                "saree": "saree", "sarees": "saree", "sari": "saree",
                "hoodie": "hoodie", "sweatshirt": "sweatshirt",
                "shorts": "shorts", "leggings": "leggings", "trousers": "trousers",
            }
            for kw, val in product_type_keywords.items():
                if kw in user_message_lower:
                    product_item_type = val
                    break

            colors = ["red", "blue", "green", "black", "white", "pink", "yellow", "orange", "purple", "brown", "grey",
                      "silver", "gold"]
            for c in colors:
                if c in user_message_lower:
                    color = c
                    break

            size_mapping = {
                "xs": "XS", "extra small": "XS",
                "s": "S", "small": "S",
                "m": "M", "medium": "M",
                "l": "L", "large": "L",
                "xl": "XL", "x-large": "XL", "extra large": "XL",
                "xxl": "XXL", "xx-large": "XXL",
            }
            for sz_key, sz_val in size_mapping.items():
                if sz_key in user_message_lower:
                    size = sz_val
                    break


        print(f"Extracted: Main Category: {main_category_preference}, Item Type: {product_item_type}, Color: {color}, Size: {size}")

        products_query = Product.objects.filter(available=True)
        combined_filters = Q()

        if main_category_preference:
            if main_category_preference == "women_clothing":
                combined_filters &= Q(gender='W')
            elif main_category_preference == "men_clothing":
                combined_filters &= Q(gender='M')
            elif main_category_preference == "kid_clothing":
                combined_filters &= Q(gender='K')
            elif main_category_preference == "shoes":
                combined_filters &= (
                    Q(category__name__icontains="shoe") | Q(subcategory__name__icontains="shoe") |
                    Q(category__name__icontains="footwear") | Q(subcategory__name__icontains="footwear") |
                    Q(gender='M', category__name__icontains="shoe") | Q(gender='W', category__name__icontains="shoe") |
                    Q(gender='U', category__name__icontains="shoe")
                )
            elif main_category_preference == "bags":
                category_or_name_q = (
                    Q(category__name__icontains="bag") | Q(subcategory__name__icontains="bag") |
                    Q(name__icontains="bag") | Q(description__icontains="bag") |
                    Q(category__name__icontains="backpack") | Q(subcategory__name__icontains="backpack") |
                    Q(name__icontains="backpack") | Q(description__icontains="backpack") |
                    Q(category__name__icontains="purse") | Q(subcategory__name__icontains="purse") |
                    Q(name__icontains="purse") | Q(description__icontains="purse") |
                    Q(category__name__icontains="luggage") | Q(subcategory__name__icontains="luggage")
                )
                combined_filters &= category_or_name_q
                combined_filters &= (
                    Q(gender='U') | Q(gender='M', category__name__icontains="bag") | Q(gender='W', category__name__icontains="bag") |
                    Q(category__name__icontains="bag")
                )
                combined_filters &= (
                    ~Q(category__name__icontains="accessories") & ~Q(subcategory__name__icontains="accessories") &
                    ~Q(category__name__icontains="jewelry") & ~Q(subcategory__name__icontains="jewelry") &
                    ~Q(category__name__icontains="jewellery") & ~Q(subcategory__name__icontains="jewellery") &
                    ~Q(name__icontains="ring") & ~Q(description__icontains="ring") &
                    ~Q(name__icontains="necklace") & ~Q(description__icontains="necklace")
                )
                combined_filters &= (
                    ~Q(category__name__icontains="clothing") & ~Q(subcategory__name__icontains="clothing") &
                    ~Q(category__name__icontains="wear") & ~Q(subcategory__name__icontains="wear") &
                    ~Q(category__name__icontains="shoe") & ~Q(subcategory__name__icontains="shoe") &
                    ~Q(category__name__icontains="footwear") & ~Q(subcategory__name__icontains="footwear")
                )

            elif main_category_preference == "accessories":
                combined_filters &= (
                    Q(category__name__icontains="accessories") |
                    Q(subcategory__name__icontains="accessories") |
                    Q(category__name__icontains="jewelry") |
                    Q(subcategory__name__icontains="jewelry") |
                    Q(category__name__icontains="jewellery") |
                    Q(subcategory__name__icontains="jewellery") |
                    Q(category__name__icontains="watches") |
                    Q(subcategory__name__icontains="watches") |
                    Q(category__name__icontains="ring") |
                    Q(subcategory__name__icontains="ring") |
                    Q(category__name__icontains="earring") |
                    Q(subcategory__name__icontains="earring") |
                    Q(category__name__icontains="necklace") |
                    Q(subcategory__name__icontains="necklace") |
                    Q(category__name__icontains="bracelet") |
                    Q(gender='U')
                )
                combined_filters &= (
                    ~Q(Q(name__icontains="saree") | Q(description__icontains="saree")) &
                    ~Q(Q(name__icontains="dress") | Q(description__icontains="dress")) &
                    ~Q(Q(name__icontains="shirt") | Q(description__icontains="shirt")) &
                    ~Q(Q(name__icontains="pant") | Q(description__icontains="pant")) &
                    ~Q(Q(name__icontains="jeans") | Q(description__icontains="jeans")) &
                    ~Q(Q(name__icontains="trouser") | Q(description__icontains="trouser")) &
                    ~Q(Q(category__name__icontains="clothing") | Q(subcategory__name__icontains="clothing")) &
                    ~Q(Q(category__name__icontains="wear") | Q(subcategory__name__icontains="wear")) &
                    ~Q(Q(category__name__icontains="shoe") | Q(subcategory__name__icontains="shoe") | Q(category__name__icontains="footwear") | Q(subcategory__name__icontains="footwear"))
                )

        if product_item_type:
            item_type_q = (
                    Q(name__icontains=product_item_type) |
                    Q(description__icontains=product_item_type) |
                    Q(category__name__icontains=product_item_type) |
                    Q(subcategory__name__icontains=product_item_type)
            )
            if combined_filters:
                combined_filters &= item_type_q
            else:
                combined_filters = item_type_q

        if color:
            color_q = Q(color__iexact=color)
            if combined_filters:
                combined_filters &= color_q
            else:
                combined_filters = color_q

        if size:
            size_q = Q(size__iexact=size)
            if combined_filters:
                combined_filters &= size_q
            else:
                combined_filters = size_q

        # If no specific product, color, or size keywords were identified,
        # but the general product search intent was predicted, use the full message
        if not (main_category_preference or product_item_type or color or size):
            combined_filters = (
                    Q(name__icontains=user_message_lower) |
                    Q(description__icontains=user_message_lower) |
                    Q(category__name__icontains=user_message_lower) |
                    Q(subcategory__name__icontains=user_message_lower)
            )
            # If the above still yields no filters, ensure it's not an empty Q() object later
            # This is primarily for very general "show me products" type queries.
            # For "red dress", it will have color and product_item_type.

        products_queryset = Product.objects.none() # Initialize as empty to prevent error

        if combined_filters: # Only apply filter if there's actually a filter to apply
            products_queryset = products_query.filter(combined_filters).distinct()

        print(f"DEBUG: Final Django Query for '{user_message_str}': {products_queryset.query}")

        products = products_queryset[:3]

        if products.exists():
            response_message = "Here are a few items we found for you:<br>"
            for p in products:
                product_url = reverse('shop:productdetail', args=[p.id])
                response_message += f"- <a href='{product_url}' target='_parent'>{p.name}</a> (₹{p.price})<br>"
            products_list_url = reverse('shop:product_list')
            response_message += f"<br>You can find more on our <a href='{products_list_url}' target='_parent'>Products page</a>."
            return response_message
        else:
            specific_query_parts = []
            if main_category_preference: specific_query_parts.append(main_category_preference.replace("_clothing", ""))
            if product_item_type: specific_query_parts.append(product_item_type)
            if color: specific_query_parts.append(color)
            if size: specific_query_parts.append(size)

            if specific_query_parts:
                message = f"Sorry, I couldn't find any {' '.join(specific_query_parts)} at the moment. Please try a different term or browse our <a href='{reverse('shop:product_list')}' target='_parent'>Products page</a>."
            else:
                # Fallback to generic product search response from JSON
                for intent in intents:
                    if intent['tag'] == 'product_search_query':
                        return random.choice(intent['responses'])
                # Ultimate fallback if 'product_search_query' intent somehow missing
                return "I couldn't find any products matching your request. What specific product or type of product are you looking for?"

    # --- General Intent Response Generation (for all other predicted_tags) ---
    # This block will execute if predicted_tag is NOT 'product_search_query'
    for intent in intents:
        if intent['tag'] == predicted_tag:
            response_template = random.choice(intent['responses'])

            # Dictionary to map internal URL placeholders to Django reverse URLs
            url_mappings = {
                "/returns/": reverse('shop:faqs'), # Assuming your returns policy is part of FAQs
                "/track-order/": reverse('shop:home'), # Placeholder, create a dedicated track order page if needed
                "/contactus/": reverse('shop:contactus'),
                "/products/": reverse('shop:product_list'),
                "/about/": reverse('shop:home'), # Placeholder, create a dedicated about page
                "/feedback/": reverse('shop:home'), # Placeholder, create a dedicated feedback page
                "/shipping-info/": reverse('shop:faqs'), # Assuming shipping info is part of FAQs
                "/promotions/": reverse('shop:home'), # Placeholder, create a dedicated promotions page
                "/size-guide/": reverse('shop:faqs'), # Assuming size guide is part of FAQs
                "/cart/": reverse('shop:home'), # Placeholder for cart page
                "/register/": reverse('shop:signup'),
                "/contactus/#complaint-form": reverse('shop:contactus'), # Direct to contact us
                "/contactus/#suggestions": reverse('shop:contactus'), # Direct to contact us
            }

            # Apply general URL replacements first
            for old_path, new_url in url_mappings.items():
                response_template = response_template.replace(f"href='{old_path}'", f"href='{new_url}'")
                response_template = response_template.replace(f"href=\"{old_path}\"", f"href=\"{new_url}\"")


            # Specific replacements for dynamic content (email, phone, etc.)
            if predicted_tag == "contact_support":
                response_template = response_template.replace("support@eterna.com", settings.EMAIL_HOST_USER)
                response_template = response_template.replace("9048376679", "9048376679") # Or from settings if applicable

            return response_template

    # Fallback if no intent (including 'fallback') was found or matched in the JSON
    # This should ideally not be reached if 'fallback' intent is correctly defined.
    return "I'm sorry, I couldn't find a suitable response. Could you please rephrase or ask about something else?"


# --- Chatbot View (Handles HTTP requests and calls the helper function) ---
@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(xframe_options_exempt, name='dispatch')
class ChatbotView(View):
    def get(self, request):
        return render(request, 'chatbot.html') # Assuming you have a chatbot.html for the iframe itself

    def post(self, request):
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            print(f"SERVER: Received message from user: '{user_message}'")

            chatbot_response_text = _get_chatbot_response_logic(user_message)

            print(f"SERVER: Chatbot response: '{chatbot_response_text}'")
            return JsonResponse({'response': chatbot_response_text})
        except json.JSONDecodeError:
            print("SERVER ERROR: Invalid JSON in request body.")
            return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
        except Exception as e:
            print(f"SERVER ERROR: An internal server error occurred in ChatbotView post method: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'An internal server error occurred: {e}'}, status=500)


# --- Existing Views (No changes below this point, they were already correct) ---
class HomeView(View):
    def get(self, request):
        categories = Category.objects.prefetch_related('subcategories').all()
        return render(request, 'home.html', {'categories': categories})


class ProductListView(ListView):
    model = Product
    template_name = 'products.html'
    context_object_name = 'products'
    paginate_by = 9

    def get_queryset(self):
        queryset = super().get_queryset().filter(available=True).order_by('-created')

        category_id = self.kwargs.get('category_id')
        if not category_id:
            category_id = self.request.GET.get('category_id')

        subcategory_id = self.kwargs.get('subcategory_id')
        if not subcategory_id:
            subcategory_id = self.request.GET.get('subcategory_id')

        if subcategory_id:
            try:
                current_subcategory = get_object_or_404(SubCategory, id=subcategory_id)
                queryset = queryset.filter(subcategory=current_subcategory)
            except ValueError:
                pass
        elif category_id:
            try:
                category = get_object_or_404(Category, id=category_id)
                queryset = queryset.filter(category=category)
            except ValueError:
                pass
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(subcategory__name__icontains=query)
            ).distinct()

        price_range = self.request.GET.get('price_range')
        if price_range:
            try:
                min_price, max_price = map(int, price_range.split('-'))
                queryset = queryset.filter(price__gte=min_price, price__lte=max_price)
            except ValueError:
                pass

        color = self.request.GET.get('color')
        if color:
            queryset = queryset.filter(color__iexact=color)

        size = self.request.GET.get('size')
        if size:
            queryset = queryset.filter(size__iexact=size)

        sort_by = self.request.GET.get('sort_by')
        if sort_by == 'popularity':
            queryset = queryset.order_by('-id')
        elif sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'latest':
            queryset = queryset.order_by('-created')
        print(queryset.query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['all_categories'] = Category.objects.annotate(
            product_count=Count('product', filter=Q(product__available=True))
        )

        current_category = None
        current_subcategory = None

        subcategory_id = self.kwargs.get('subcategory_id') or self.request.GET.get('subcategory_id')
        if subcategory_id:
            current_subcategory = get_object_or_404(SubCategory, id=subcategory_id)
            current_category = current_subcategory.category
        else:
            category_id = self.kwargs.get('category_id') or self.request.GET.get('category_id')
            if category_id:
                current_category = get_object_or_404(Category, id=category_id)

        context['current_category'] = current_category
        context['current_subcategory'] = current_subcategory

        context['available_colors'] = Product.objects.filter(available=True).exclude(color__isnull=True).exclude(color__exact='').values_list('color', flat=True).distinct().order_by('color')
        context['available_sizes'] = Product.objects.filter(available=True).exclude(size__isnull=True).exclude(size__exact='').values_list('size', flat=True).distinct().order_by('size')

        context['total_products_count'] = Product.objects.filter(available=True).count()

        context['cart_item_count'] = 0
        context['favorite_item_count'] = 0

        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'productdetail.html'
    context_object_name = 'product'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart_item_count'] = 0
        context['favorite_item_count'] = 0
        return context


class SignupView(View):
    def post(self,request):
        form_instance=SignupForm(request.POST)
        if form_instance.is_valid():
            user=form_instance.save(commit=False)
            user.is_active=False
            user.save()
            user.generate_otp()
            send_mail(
                "Ecommerce1 OTP",
                user.otp,
                "sethulakshmi1496@gmail.com",
                [user.email],
                fail_silently=False,
            )
            print('OTP sent to:', user.email)
            return redirect('shop:verify')
        else:
            return render(request, 'signup.html', {'form': form_instance})

    def get(self,request):
        form_instance=SignupForm()
        return render(request,'signup.html',{'form':form_instance})


class OtpVerificationView(View):
    def post(self,request):
        otp=request.POST.get('otp')
        print("Received OTP for verification:", otp)
        try:
            u=CustomUser.objects.get(otp=otp)
            u.is_active=True
            u.is_verified=True
            u.otp=None
            u.save()
            messages.success(request, "Account verified successfully! You can now log in.")
            return redirect('shop:signin')
        except CustomUser.DoesNotExist:
            messages.error(request,"Invalid OTP. Please try again.")
            return redirect('shop:verify')
    def get(self,request):
        return render(request,'otp_verify.html')


class SigninView(View):
    def post(self,request):
        form_instance=LoginForm(request.POST)
        if form_instance.is_valid():
            name=form_instance.cleaned_data['username']
            pwd=form_instance.cleaned_data['password']
            user=authenticate(request, username=name,password=pwd)
            if user is not None:
                if user.is_active:
                    login(request,user)
                    if user.is_superuser:
                        messages.success(request, f"Welcome, Admin {user.username}!")
                        return redirect('shop:home')
                    else:
                        messages.success(request, f"Welcome, {user.username}!")
                        return redirect('shop:home')
                else:
                    messages.warning(request, "Your account is not active. Please verify your OTP.")
                    return redirect('shop:verify')
            else:
                messages.error(request, "Invalid username or password.")
                return redirect('shop:signin')
        else:
            messages.error(request, "Please enter both username and password.")
            return render(request, 'login.html', {'form': form_instance})

    def get(self,request):
        form_instance=LoginForm()
        return render(request,'login.html',{'form':form_instance})


class SignOutView(View):
    def get(self,request):
        logout(request)
        messages.info(request, "You have been successfully logged out.")
        return redirect('shop:signin')


class HelpView(View):
    def get(self, request):
        return render(request, 'help.html')

class SupportView(View):
    def get(self, request):
        return render(request, 'support.html')

class FaqsView(View):
    def get(self, request):
        return render(request, 'faqs.html')

class ContactusView(View):
    def get(self, request):
        return render(request, 'contactus.html')


class AddCategoryView(View):
    def get(self, request):
        form_instance = CategoryForm()
        return render(request, 'add_category.html', {'form': form_instance})
    def post(self,request):
        form_instance=CategoryForm(request.POST,request.FILES)
        if form_instance.is_valid():
            form_instance.save()
            messages.success(request, "Category added successfully!")
            return redirect('shop:home')
        else:
            messages.error(request, "Error adding category. Please check your input.")
            return render(request, 'add_category.html', {'form': form_instance})


class AddProductView(View):
    def get(self,request):
        form_instance=ProductForm()
        return render(request,'add_product.html',{'form':form_instance})
    def post(self,request):
        form_instance=ProductForm(request.POST,request.FILES)
        if form_instance.is_valid():
            form_instance.save()
            messages.success(request, "Product added successfully!")
            return redirect('shop:home')
        else:
            messages.error(request, "Error adding product. Please check your input.")
            return render(request, 'add_product.html', {'form': form_instance})