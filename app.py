from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from db_config import db_config
import os
import tensorflow as tf
import numpy as np
from PIL import Image
import pymysql
from flask import Flask, request, jsonify
from flask import send_from_directory
from flask_cors import CORS

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
CORS(app, origins=["http://127.0.0.1:5000"])

# Load CNN model
model = tf.keras.models.load_model('model\model2_mobilenetv2.h5')
classes = ['berminyak', 'jerawat', 'normal']

# DB connection
def get_db():
    return pymysql.connect(**db_config)

# Preprocessing
def preprocess_image(image_path):
    img = Image.open(image_path).convert("RGB").resize((224, 224))
    img_array = np.array(img) / 255.0
    return np.expand_dims(img_array, axis=0)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)

            # Predict
            input_tensor = preprocess_image(filepath)
            pred = model.predict(input_tensor)
            result = classes[np.argmax(pred)]

            # Save to DB
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO predictions (filename, result) VALUES (%s, %s)", (filename, result))
            conn.commit()
            cursor.close()
            conn.close()

            return render_template('result.html', result=result, image_path=filepath)

    return render_template('index.html')


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/skincheck', methods=['POST'])
def skincheck_api():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image = request.files['image']
    try:
        img = Image.open(image).convert("RGB").resize((224, 224))
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        pred = model.predict(img_array)
        label = np.argmax(pred)
        print("Prediksi mentah:", pred)
        print("Prediksi final:", classes[label])

        return jsonify({'label': classes[label], 'confidence': float(np.max(pred))})
    except Exception as e:
        print(e)
        return jsonify({'error': 'Prediction failed', 'details': str(e)}), 500



if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.mkdir('uploads')
    app.run(debug=True)
