from distutils.log import debug
import qrcode
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from flask import Flask, flash, render_template, Response, redirect, url_for, request, send_from_directory, abort
import os
import urllib.request
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
import secrets

app = Flask(__name__)



UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_PATH'] = UPLOAD_FOLDER 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.jpeg']
app.secret_key = "secret key"

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

class QrForm(FlaskForm):
    data = StringField("Qr information", validators = [DataRequired(), Length(min=2, max=1000)])
    submit = SubmitField("Generate QR")



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#Setting the web cam for capture

cam = cv2.VideoCapture(0) #open cv stars the main camera in the device 
cam.set(3,640)
cam.set(4,480)

def read_qr():
    
    while cam.isOpened():
    
        success, img = cam.read()
        for output in decode(img): # pyzbar decode de qr images
            text = output.data.decode("utf-8") #this line takes only de text information out of the qr code
            points = np.array([output.polygon],np.int32)
            points = points.reshape((-1,1,2))
            cv2.polylines(img,[points], True, (0,0,255),5)
            corner = output.rect
            cv2.putText(img, text, (corner[0], corner[1]), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (25,25,25),2)

#this block makes posible the web streaming
        ret, buffer = cv2.imencode(".jpg", img) 
        img = buffer.tobytes()
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')
        
    cam.release()
    cv2.destroyAllWindows()
    


@app.route("/")
def index():
    return render_template("index.html", title="Qr Reader")


@app.route("/webcam_reader")
def video_feed():
    return Response(read_qr(), 
    mimetype = "multipart/x-mixed-replace; boundary=frame")

""" The qr reader gets an image and decode the text inside."""

@app.route("/image_reader", methods=['GET','POST'])

def image_reader():
    
    return render_template("image_reader.html", title="Qr image reader")
         
              
@app.route("/upload", methods=['GET','POST'])

def upload_file():                                        
        if request.method == 'POST':
                uploaded_file = request.files['file']
               
                filename = secure_filename(uploaded_file.filename)
                file_ext = os.path.splitext(filename)[1]
                if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                    abort(400)
                    
                uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
                path = f"{app.config['UPLOAD_PATH']}/{filename}"
                image = cv2.imread(path)  # like the web cam, open cv read uploaded images and pyzbar decode them.
                data = decode(image)
                for output in data:
                    qr_text = output.data.decode("utf-8")
                
                return render_template('image_reader.html', filename=filename, qr_text = qr_text)  
        else:
            return render_template("image_reader.html", title="Qr image reader")

@app.route('/display_image/<filename>')
def display_image(filename):
    return send_from_directory(app.config['UPLOAD_PATH'], filename)   
    

"""Using qrcode library we can create qr codes and download them"""

@app.route('/qr_creator', methods=['GET', 'POST'])


def qr_creator():
    form = QrForm()

    if request.method == 'POST':

        if form.validate_on_submit():
            data = form.data.data
            
            image_name = f"{secrets.token_hex(10)}.png"
            qrcode_location = f"{app.config['UPLOAD_PATH']}/{image_name}"

        # Qrcode usage is very straightforward, this block, from the official documentation makes the qr and let some configurations

            try:
                qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=20,
                border=4)
                qr.add_data(str(data))
                qr.make(fit = True)
                    
                img = qr.make_image(fill_color = "purple",
                   back_color = "white")
                
                img.save(qrcode_location)
            except Exception as e:
                print(e)
        return render_template("qr_generated.html", title="Qr done", image = image_name, data = data)

    else:
         return render_template("qr_creator.html", title="Qr creator", form=form)


    


if __name__ == "__main__":
    app.run()

cam.release()
cv2.destroyAllWindows()