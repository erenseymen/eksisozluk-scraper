from flask import Flask, render_template, request, send_file, session
import pandas as pd
import os
from io import BytesIO
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.secret_key = os.urandom(24)  # Required for session

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    if file:
        try:
            df = pd.read_csv(file)
            # Identify duplicates across all columns
            duplicates = df[df.duplicated(keep=False)]
            
            # Store duplicates DataFrame in session using a unique ID
            # We'll store it as CSV string in session (or use temp file)
            # For simplicity, we'll use a temporary file approach
            session_id = str(uuid.uuid4())
            
            # Clean up any previous duplicates file
            if 'duplicates_file' in session and os.path.exists(session['duplicates_file']):
                try:
                    os.remove(session['duplicates_file'])
                except:
                    pass
            
            # Save duplicates to a temporary CSV file
            if not duplicates.empty:
                temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'duplicates_{session_id}.csv')
                duplicates.to_csv(temp_file_path, index=False)
                session['duplicates_file'] = temp_file_path
                session['has_duplicates'] = True
            else:
                session['has_duplicates'] = False
                session.pop('duplicates_file', None)
            
            return render_template('results.html',
                                  original_data=df.to_html(classes='table table-striped', index=False),
                                  duplicate_data=duplicates.to_html(classes='table table-striped', index=False) if not duplicates.empty else None,
                                  has_duplicates=not duplicates.empty)
        except Exception as e:
            return f"Error processing file: {e}", 500
    return "Something went wrong", 500

@app.route('/download_duplicates', methods=['GET'])
def download_duplicates():
    # Retrieve the duplicates file path from session
    if 'duplicates_file' not in session or not session.get('has_duplicates', False):
        return "No duplicates file available. Please upload a CSV file first.", 404
    
    duplicates_file_path = session['duplicates_file']
    
    # Check if file exists
    if not os.path.exists(duplicates_file_path):
        return "Duplicates file not found. Please upload a CSV file again.", 404
    
    # Read the duplicates DataFrame
    try:
        duplicates_df = pd.read_csv(duplicates_file_path)
        
        # Create a BytesIO object to hold the CSV data
        output = BytesIO()
        duplicates_df.to_csv(output, index=False)
        output.seek(0)
        
        # Send the file
        # Note: We don't clean up the file here so users can download multiple times
        # The file will be cleaned up when a new file is uploaded
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='duplicates.csv'
        )
    except Exception as e:
        return f"Error generating download file: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)

