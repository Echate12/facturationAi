import os
import json
import re
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import cohere
from dotenv import load_dotenv
from io import BytesIO

# Load environment variables
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
PORT = int(os.getenv("PORT", 5000))

# Validate API key
if not COHERE_API_KEY:
    print("❌ COHERE_API_KEY is missing from .env")
    exit(1)
else:
    print("✅ COHERE_API_KEY loaded successfully")

# Initialize Cohere client
co = cohere.Client(COHERE_API_KEY)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

@app.route('/api/parse', methods=['POST'])
def parse():
    """AI endpoint to parse user prompts into structured invoice items"""
    data = request.get_json()
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    # Create AI prompt for Cohere
    cohere_prompt = f"""
Extract invoice items from the following text and return a JSON array.
Each item should have: reference (if available), name, quantity, unit_price.

Text: {prompt}

Important: If a reference number is provided in the text (like 'Ref#123' or 'REF-456'), use that exact reference number.
If no reference is provided, leave the reference field empty.

Return only valid JSON array like:
[
  {{"reference": "REF123", "name": "Product Name", "quantity": 2, "unit_price": 10.50}},
  {{"reference": "", "name": "Another Product", "quantity": 1, "unit_price": 25.00}}
]
"""

    try:
        # Call Cohere API
        response = co.generate(
            model='command',
            prompt=cohere_prompt,
            max_tokens=500,
            temperature=0,
            stop_sequences=["\n\n"]
        )
        
        response_text = response.generations[0].text.strip()
        print(f"🤖 Cohere response: {response_text}")
        
        # Parse JSON from response
        items = []
        try:
            # Try direct JSON parsing
            items = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON array from text
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group(0))
            else:
                return jsonify({'error': "Couldn't parse JSON from AI response"}), 500
        
        print(f"✅ Parsed {len(items)} items successfully")
        return jsonify({'items': items})
        
    except Exception as e:
        print(f"❌ Error in /api/parse: {str(e)}")
        return jsonify({'error': f'AI parsing failed: {str(e)}'}), 500

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate PDF document from parsed items"""
    data = request.get_json()
    items = data.get('items', [])
    doc_type = data.get('docType', 'Invoice')
    
    if not items or not isinstance(items, list):
        return jsonify({'error': 'Items are required'}), 400

    try:
        # Create PDF buffer
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width / 2, height - 50, doc_type)
        
        # Date
        c.setFont("Helvetica", 12)
        from datetime import datetime
        c.drawString(50, height - 80, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        
        # Table header
        y_position = height - 120
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, "#")
        c.drawString(80, y_position, "Reference")
        c.drawString(180, y_position, "Name")
        c.drawString(350, y_position, "Qty")
        c.drawString(420, y_position, "Unit Price")
        c.drawString(500, y_position, "Total")
        
        # Items
        y_position -= 25
        c.setFont("Helvetica", 10)
        total_amount = 0
        
        for idx, item in enumerate(items, 1):
            reference = item.get('reference', 'N/A')
            name = item.get('name', '')
            quantity = item.get('quantity', 0)
            unit_price = item.get('unit_price', 0)
            line_total = quantity * unit_price
            total_amount += line_total
            
            c.drawString(50, y_position, str(idx))
            c.drawString(80, y_position, str(reference))
            c.drawString(180, y_position, str(name))
            c.drawString(350, y_position, str(quantity))
            c.drawString(420, y_position, f"${unit_price:.2f}")
            c.drawString(500, y_position, f"${line_total:.2f}")
            
            y_position -= 20
            
            # New page if needed
            if y_position < 100:
                c.showPage()
                y_position = height - 50
        
        # Total
        c.setFont("Helvetica-Bold", 14)
        c.drawString(420, y_position - 20, "TOTAL:")
        c.drawString(500, y_position - 20, f"${total_amount:.2f}")
        
        c.save()
        buffer.seek(0)
        
        print(f"✅ PDF generated with {len(items)} items")
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{doc_type.lower().replace(' ', '_')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}")
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'AI Facturation Backend is running'})

if __name__ == '__main__':
    print(f"🚀 Starting AI Facturation Backend...")
    print(f"✅ Backend running on http://localhost:{PORT}")
    print(f"📝 Available endpoints:")
    print(f"   - POST /api/parse (AI parsing)")
    print(f"   - POST /api/generate-pdf (PDF generation)")
    print(f"   - GET /health (health check)")
    app.run(host='0.0.0.0', port=PORT, debug=True) 