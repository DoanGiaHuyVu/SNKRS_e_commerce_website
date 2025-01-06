from flask import Flask, render_template, jsonify, redirect, url_for, request, session
from stripe.api_resources import checkout
import stripe
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')


class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shoes.db'  # Same database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load Stripe API keys from environment variables
# stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
stripe.api_key = os.environ.get("STRIPE_PRIVATE_API_KEY")
# 'sk_test_51QXC2BDnG13PNcpKutHjiPXMUQI6CRN20qNKyYYcnbCfI63c2x1Caf9B2OMl7Nifpmzy7U7gLVqqgRUUXELWgTrq00HRexWikM'


class Shoes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(250), nullable=False)
    product_subtitle = db.Column(db.String(250), nullable=True)
    product_gender = db.Column(db.String(250), nullable=True)
    product_price = db.Column(db.String(250), nullable=True)
    first_image_link = db.Column(db.String(250), nullable=True)
    product_data = db.Column(db.String, nullable=True)  # Storing serialized dictionary data


@app.route('/')
def home():
    PRODUCTS = db.session.execute(db.select(Shoes).order_by(Shoes.product_price))
    products = PRODUCTS.scalars().all()
    return render_template('index.html', products=products,
                           stripe_public_key=os.environ.get('STRIPE_PUBLIC_KEY'))

@app.route('/shoes/<string:gender>')
def shoes_by_gender(gender):
    PRODUCTS = db.session.execute(
        db.select(Shoes).filter_by(product_gender=gender).order_by(Shoes.product_price)
    )
    products = PRODUCTS.scalars().all()
    if not products:
        return f"No shoes found for {gender}.", 404

        # Render the template with the filtered products
    return render_template('index.html', products=products,
                           stripe_public_key=os.environ.get('STRIPE_PUBLIC_KEY'))


@app.route('/product/<int:product_id>')
def show_product(product_id):
    requested_product = db.get_or_404(Shoes, product_id)
    requested_product_data = json.loads(requested_product.product_data)
    print(requested_product_data)
    print(requested_product_data['first_image_link'])
    print(requested_product_data['other_media'])

    return render_template('shoes.html',
                           product=requested_product,
                           product_first_image_link=requested_product_data['first_image_link'],
                           product_video_link=requested_product_data['video_link'],
                           product_other_media=requested_product_data['other_media'],
                           stripe_public_key=os.environ.get('STRIPE_PUBLIC_KEY'))


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    # Fetch the product from the database
    product = db.get_or_404(Shoes, product_id)

    # Retrieve the cart from the session, or create an empty cart if it doesn't exist
    cart = session.get('cart', [])

    # Add the product to the cart
    cart.append({
        'product_id': product.id,
        'product_name': product.product_name,
        'product_price': product.product_price,
        'first_image_link': product.first_image_link
    })

    # Update the session with the new cart data
    session['cart'] = cart

    # Optionally print the session to verify
    print(f"Cart: {session['cart']}")

    # Redirect to the cart page or any other page
    return redirect(url_for('show_cart'))


@app.route('/cart')
def show_cart():
    # Retrieve the cart from the session
    cart = session.get('cart', [])
    print(cart)

    # Render the cart page with the list of items in the cart
    return render_template('cart.html', cart=cart,
                           stripe_public_key=os.environ.get('STRIPE_PUBLIC_KEY'))


@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)  # Remove the cart from the session
    return redirect(url_for('show_cart'))


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    # Get the current cart from the session
    cart = session.get('cart', [])

    # Filter out the item to be removed based on product_id
    cart = [item for item in cart if item['product_id'] != product_id]

    # Update the session with the new cart after removal
    session['cart'] = cart

    # Redirect to the cart page or wherever appropriate
    return redirect(url_for('show_cart'))


@app.route('/checkout', methods=['POST'])
def create_checkout_session():
    # PRODUCTS = db.session.execute(db.select(Shoes).order_by(Shoes.product_price))
    # products = PRODUCTS.scalars().all()

    data = request.get_json()
    print(data)
    product_id = int(data['productId'])

    # Find the product in the list
    product = db.get_or_404(Shoes, product_id)
    # print(f"Received productId: {product_id}")
    # print(f"Product name: {product}")
    # print(product.product_price[1:])
    # print(type(product.product_price[1:]))

    try:
        # Create a Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'cad',
                    'product_data': {
                        'name': product.product_name,
                        'images': [product.first_image_link],
                    },
                    'unit_amount': int(float(product.product_price[1:]) * 100),  # Replace with dynamic price
                },
                'quantity': 1,
            },
            ],
            mode='payment',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('cancel', _external=True),
        )
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403


@app.route('/checkout_cart', methods=['POST'])
def create_cart_checkout_session():
    cart = session.get('cart', [])

    # If the cart is empty, return an error response
    if not cart:
        return jsonify(error="Cart is empty"), 400

    try:
        # Create a list of line items for Stripe checkout session from the cart
        line_items = []
        for item in cart:
            # Each product in the cart is added as a line item
            line_items.append({
                'price_data': {
                    'currency': 'cad',
                    'product_data': {
                        'name': item['product_name'],
                        'images': [item['first_image_link']],
                    },
                    'unit_amount': int(float(item['product_price'][1:]) * 100),  # Convert price to cents
                },
                'quantity': 1,  # Adjust the quantity accordingly if necessary
            })

        # Create the Stripe Checkout session with all the cart items
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('cancel', _external=True),
        )
        # Return the session ID for the front-end to redirect to Stripe Checkout
        print("Stripe session created:", checkout_session.id)
        return jsonify({'id': checkout_session.id})

    except Exception as e:
        # Handle exceptions (like Stripe errors)
        print("Error creating checkout session:", e)
        return jsonify(error=str(e)), 403


@app.route('/success')
def success():
    return render_template('success.html')


@app.route('/cancel')
def cancel():
    return render_template('cancel.html')


if __name__ == '__main__':
    app.run(debug=True)
