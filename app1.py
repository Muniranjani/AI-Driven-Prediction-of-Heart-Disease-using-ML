from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import datetime


import joblib

app = Flask(__name__)

app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///heart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.Integer, nullable=False)
    trestbps = db.Column(db.Integer, nullable=False)
    chol = db.Column(db.Integer, nullable=False)
    heartrate = db.Column(db.Integer, nullable=False)
    smoker = db.Column(db.Integer, nullable=False)
    diabetes = db.Column(db.Integer, nullable=True)
    risk = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()





model = joblib.load("xgb_heart_risk_rule_model.joblib")

def label_risk(age, gender, trestbps, chol, heartrate, smoker):
    # This can be customized based on the trained model
    risk = 0
    if (
        heartrate <= 60 or heartrate >= 100 or
        trestbps <= 90 or trestbps >= 140 or
        chol <= 130 or chol >= 200 or
        smoker == 1 or
        age > 50
    ):
        risk = 1
    return risk



@app.route('/users')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=all_users)



@app.route('/')
def home():
    return render_template('index.html')



@app.route('/start', methods=['POST'])
def start():
    return redirect(url_for('basic_info'))



@app.route('/basic_info', methods=['GET', 'POST'])
def basic_info():
    if request.method == 'POST':
        session['username'] = request.form['username']
        session['email'] = request.form['email']
        session['phone'] = request.form['phone']
        session['age'] = int(request.form['age'])
        session['gender'] = int(request.form['gender'])
        return redirect(url_for('medical_info'))
    return render_template('basic_info.html')


@app.route('/medical_info', methods=['GET', 'POST'])
def medical_info():
    if request.method == 'POST':
        # Collect medical data from form
        session['trestbps'] = int(request.form['trestbps'])
        session['chol'] = int(request.form['chol'])
        session['heartrate'] = int(request.form['heartrate'])
        session['smoker'] = int(request.form['smoker'])

        # Calculate risk
        risk = label_risk(
            session['age'],
            session['gender'],
            session['trestbps'],
            session['chol'],
            session['heartrate'],
            session['smoker']
        )
        session['risk'] = risk

        # Generate recommendations
        recommendations = get_recommendations(risk)
        session['recommendations'] = recommendations

        # 🔽 ✅ SAVE user to the database here
        new_user = User(
            username=session['username'],
            email=session['email'],
            phone=session['phone'],
            age=session['age'],
            gender=session['gender'],
            trestbps=session['trestbps'],
            chol=session['chol'],
            heartrate=session['heartrate'],
            smoker=session['smoker'],
            diabetes=session.get('diabetes', 0),
            risk=risk
        )
        db.session.add(new_user)
        db.session.commit()  # ✅ This saves it
        print("User saved to DB ✅")

        # Then redirect to result page
        return redirect(url_for('result'))

    # Show the form if it's a GET request
    return render_template('medical_info.html')



@app.route('/result')
def result():
    name = session.get('username')
    email = session.get('email')
    phone = session.get('phone')
    age = session.get('age')
    gender = 'Male' if session.get('gender') == 1 else 'Female'
    cholesterol = session.get('chol')
    blood_pressure = session.get('trestbps')
    heart_rate = session.get('heartrate')
    smoker = 'Yes' if session.get('smoker') == 1 else 'No'
    risk = session.get('risk')
    recommendations = session.get('recommendations')

    # Compute risk again if needed
    risk_points = 0
    if cholesterol >= 240:
        risk_points += 2
    elif 200 <= cholesterol < 240:
        risk_points += 1
    if blood_pressure >= 140:
        risk_points += 2
    elif 120 <= blood_pressure < 140:
        risk_points += 1
    if heart_rate > 100 or heart_rate < 60:
        risk_points += 1
    if smoker == 'Yes':
        risk_points += 2
    if age >= 55:
        risk_points += 1

    if risk_points >= 5:
        risk_status = 'High Risk'
        message = 'You are at high risk of heart disease. Immediate lifestyle changes are necessary.'
    elif risk_points >= 2:
        risk_status = 'Moderate Risk'
        message = 'You are at moderate risk of heart disease. Consider regular checkups and lifestyle improvements.'
    else:
        risk_status = 'Low Risk'
        message = 'You are at low risk of heart disease. Keep maintaining a healthy lifestyle.'

    return render_template('result.html',
                           name=name,
                           email=email,
                           phone=phone,
                           age=age,
                           gender=gender,
                           cholesterol=cholesterol,
                           blood_pressure=blood_pressure,
                           heart_rate=heart_rate,
                           smoker=smoker,
                           risk_status=risk_status,
                           message=message,
                           recommendations=recommendations)

@app.route('/submit', methods=['POST'])
def submit():
    # Example: after processing user form inputs, set session variables
    session['chol'] = int(request.form.get('cholesterol', 0))
    session['trestbps'] = int(request.form.get('blood_pressure', 0))
    session['heartrate'] = int(request.form.get('heart_rate', 0))
    session['smoker'] = int(request.form.get('smoker', 0))
    session['diabetes'] = int(request.form.get('diabetes', 0))

    # Risk could be determined by your prediction model, for example:
    risk = int(request.form.get('risk', 0))  # 1 for high risk, 0 for low risk
    
    # Save risk to session or pass directly
    session['risk'] = risk
    
    return redirect(url_for('recommendation'))


@app.route('/recommendation')
def recommendation():
    risk = session.get('risk', 0)
    recommendations = get_recommendations(risk)
    return render_template('recommendation.html', recommendations=recommendations)


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

def get_recommendations(risk):
    if risk == 1:
        recommendations = {
            'summary': "You are at high risk of heart disease. Immediate lifestyle changes are necessary.",
            'diet': [
                "Avoid saturated and trans fats.",
                "Eat more fiber-rich foods like oats, beans, and whole grains.",
                "Limit salt intake to under 1,500 mg per day.",
                "Drink plenty of water, avoid sugary beverages.",
                "Include omega-3 fatty acids from fish like salmon.",
                "Avoid processed and fast foods.",
                "Increase intake of antioxidants such as berries and dark leafy greens."
                "Switch to plant-based meals several times a week to reduce saturated fat.",
"Consume foods rich in potassium such as bananas, sweet potatoes, and spinach to help control blood pressure.",
"Replace red meat with fish, legumes, and tofu.",
"Use herbs and spices instead of salt to flavor food.",
"Choose low-fat dairy or dairy alternatives.",

            ],
            'exercise': [
                "Start with walking 30 minutes daily.",
                "Gradually add jogging or cycling.",
                "Include strength training twice a week.",
                "Practice deep breathing or yoga for stress management.",
                "Try swimming or low-impact aerobics for cardiovascular health.",
                "Avoid sudden intense exercise; warm up and cool down properly."
                "Use a fitness tracker or app to monitor your physical activity and stay motivated.",
"Try Tai Chi or Pilates for gentle movement and heart health.",
"Break exercise into smaller chunks (e.g., 3 x 10-minute walks).",
"Walk or bike to nearby errands instead of driving.",
"Join a heart-friendly exercise class designed for older adults or those with heart conditions.",

            ],
            'routine': [
                "Wake up by 6–7 AM daily.",
                "Start with warm water and stretching.",
                "Have regular meal times.",
                "Avoid screen time during meals, sleep by 10 PM.",
                "Keep stress journals to monitor triggers.",
                "Schedule regular health check-ups.",
                "Limit alcohol consumption to moderate levels."
                "Include 10 minutes of morning sunlight to support circadian rhythm and mood.",
"Plan weekly meals and groceries ahead to support a heart-healthy diet.",
"Practice gratitude journaling to reduce chronic stress.",
"Use meditation apps (like Headspace or Calm) to build daily mindfulness habits.",
"Limit social media use after 8 PM to promote better sleep hygiene.",

            ],
            'specific': []
        }

        # Add specific tips based on user's input
        if session.get('chol', 0) > 200:
            recommendations['specific'].append("Cholesterol is high: Avoid fried foods, eat oats and legumes regularly.")
        if session.get('trestbps', 0) > 140:
            recommendations['specific'].append("High blood pressure: Avoid salty snacks, reduce caffeine/alcohol.")
        if session.get('heartrate', 60) < 60 or session.get('heartrate', 60) > 100:
            recommendations['specific'].append("Abnormal heart rate: Reduce stress, avoid caffeine, practice breathing.")
        if session.get('smoker', 0) == 1:
            recommendations['specific'].append("You smoke: Quitting significantly reduces heart risk.")
        if session.get('diabetes', 0) == 1:
            recommendations['specific'].append("Manage diabetes with diet and medication as prescribed.")
        if session.get('chol', 0) > 240:
            recommendations['specific'].append("Very high cholesterol: Consult a cardiologist for possible medications.")
        if session.get('age', 0) > 60:
            recommendations['specific'].append("Due to your age, consider a routine ECG and annual cardiac screening.")
        if session.get('gender', 0) == 0:  # Female
            recommendations['specific'].append("Women may experience atypical symptoms of heart disease. Stay informed and monitor any changes.")
        if session.get('diabetes', 0) == 1:
            recommendations['specific'].append("Maintain blood glucose logs and consult a diabetes educator every 3–6 months.")


    else:
        recommendations = {
            'summary': "You are currently at low risk. Continue maintaining a healthy lifestyle.",
            'diet': [
                "Maintain a balanced diet with fruits, vegetables, whole grains.",
                "Include lean proteins like chicken or tofu.",
                "Stay hydrated with 8–10 glasses of water.",
                "Limit intake of processed sugars and snacks.",
                "Include nuts and seeds for healthy fats."
                "Try one new vegetable or healthy recipe each week to keep your meals interesting.",
"Make smoothies with leafy greens and berries for heart-healthy breakfasts.",
"Include fermented foods like yogurt, kimchi, or kefir for gut and heart health.",

            ],
            'exercise': [
                "Engage in 30 minutes of moderate activity 5 days/week.",
                "Take walking breaks if at a desk often.",
                "Stretch or do yoga to stay flexible.",
                "Try group activities or sports to stay motivated."
                "Explore outdoor activities like hiking or biking to enjoy nature while staying fit.",
"Use standing desks or take walking calls to avoid sedentary time.",
"Follow online cardio or dance classes for fun, engaging workouts at home.",

            ],
            'routine': [
                "Stick to a consistent sleep schedule.",
                "Eat meals at regular intervals.",
                "Check your health every 6 months.",
                "Manage stress through mindfulness or hobbies.",
                "Limit screen time before bed."
                "Follow a digital detox routine for at least 1 hour before bed.",
"Keep a weekly planner to manage time and reduce mental clutter.",
"Join a community group or volunteer to stay socially active and mentally sharp.",

            ],
            'specific': []
        }

    return recommendations

   

if __name__ == '__main__':
    app.run(debug=True)
