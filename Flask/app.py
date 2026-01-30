from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

# Home page
@app.route('/')
def home():
    return render_template('home.html')

# About Us page
@app.route('/about')
def about():
    return render_template('about.html')

# Settings page
@app.route('/settings')
def settings():
    return render_template('settings.html')

# Customer dashboard page
@app.route('/continue')
def go_continue():
    return redirect(url_for('dashboard'))

# Customer dashboard page
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Day Care page
@app.route('/day_care')
def day_care():
    return render_template('day_care.html')  # optional if you add separate page later

# Appointments page
@app.route('/appointments')
def appointments():
    return render_template('appointments.html')  # optional if you add separate page later


if __name__ == '__main__':
    app.run(debug=True)
