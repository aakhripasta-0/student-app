from flask import Flask, render_template, request, redirect
import os
from datetime import datetime
import uuid
from google_sheets_utils import get_all_rows, write_all_rows

app = Flask(__name__)

# ---------- Utility Functions ----------
def load_students():
    return get_all_rows("students")

def save_students(students):
    header = ['id', 'name', 'parent_name', 'class', 'school', 'board', 'category',
              'admission_date', 'fees', 'contact', 'parent_contact', 'installments', 'first_installment_amount']
    write_all_rows("students", students, header)

def get_student_by_id(student_id):
    return next((s for s in load_students() if s['id'] == student_id), None)

def load_fees_data(class_):
    return get_all_rows(f"fees_{class_}")

def save_fees_data(class_, data):
    header = ['student_id', 'installment_no', 'amount', 'date']
    write_all_rows(f"fees_{class_}", data, header)

# ---------- Routes ----------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        try:
            fees = int(request.form['fees'])
            first_installment = int(request.form.get('first_installment_amount', 0))
            installments = int(request.form.get('installments', 1))
        except ValueError:
            return "Invalid numeric inputs.", 400

        student_id = str(uuid.uuid4())
        class_ = request.form['class']
        admission_date = request.form['admission_date']

        student = {
            'id': student_id,
            'name': request.form['name'],
            'parent_name': request.form['parent_name'],
            'class': class_,
            'school': request.form['school'],
            'board': request.form['board'],
            'category': request.form['category'],
            'admission_date': admission_date,
            'fees': str(fees),
            'contact': request.form['contact'],
            'parent_contact': request.form['parent_contact'],
            'installments': str(installments),
            'first_installment_amount': str(first_installment)
        }

        students = load_students()
        students.append(student)
        save_students(students)

        fees_data = load_fees_data(class_)
        if first_installment > 0:
            fees_data.append({
                'student_id': student_id,
                'installment_no': '1',
                'amount': str(first_installment),
                'date': admission_date
            })
            save_fees_data(class_, fees_data)

        return redirect('/view_students')

    return render_template('add_student.html', student=None)

@app.route('/view_students')
def view_students():
    selected_class = request.args.get('class')
    students = load_students()
    if selected_class:
        students = [s for s in students if s['class'] == selected_class]
    students.sort(key=lambda s: s['name'].lower())
    return render_template('view_students.html', students=students, selected_class=selected_class, total_students=len(students))

@app.route('/delete_student/<student_id>')
def delete_student(student_id):
    students = load_students()
    student = get_student_by_id(student_id)
    if student:
        class_ = student['class']
        students = [s for s in students if s['id'] != student_id]
        save_students(students)
        fees_data = load_fees_data(class_)
        fees_data = [f for f in fees_data if f['student_id'] != student_id]
        save_fees_data(class_, fees_data)
    return redirect('/view_students')

@app.route('/edit_student/<student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    students = load_students()
    student = get_student_by_id(student_id)
    if request.method == 'POST':
        for s in students:
            if s['id'] == student_id:
                s.update({
                    'name': request.form['name'],
                    'parent_name': request.form['parent_name'],
                    'class': request.form['class'],
                    'school': request.form['school'],
                    'board': request.form['board'],
                    'category': request.form['category'],
                    'admission_date': request.form['admission_date'],
                    'fees': request.form['fees'],
                    'contact': request.form['contact'],
                    'parent_contact': request.form['parent_contact'],
                    'installments': request.form['installments'],
                    'first_installment_amount': request.form['first_installment_amount']
                })
                break
        save_students(students)
        return redirect('/view_students')
    return render_template('add_student.html', student=student)

@app.route('/fees_management')
def fees_management():
    selected_class = request.args.get('class', '')
    student_id = request.args.get('student', '')
    students = [s for s in load_students() if s['class'] == selected_class] if selected_class else []
    selected_student = next((s for s in students if s['id'] == student_id), None)

    installments = []
    remaining = None
    next_no = 1

    if selected_student:
        fees_data = load_fees_data(selected_class)
        student_fees = [f for f in fees_data if f['student_id'] == student_id]
        installments = sorted(student_fees, key=lambda x: int(x['installment_no']))
        total_paid = sum(int(i['amount']) for i in installments)
        remaining = int(selected_student['fees']) - total_paid
        next_no = len(installments) + 1

    return render_template('fees_management.html', selected_class=selected_class,
                           students=students, selected_student=selected_student,
                           installments=installments, remaining=remaining,
                           next_installment_number=next_no)

@app.route('/submit_installment', methods=['POST'])
def submit_installment():
    student_id = request.form['student_id']
    amount = int(request.form['amount'])
    date = request.form['date']
    installment_no = int(request.form['installment_no'])

    student = get_student_by_id(student_id)
    if not student:
        return redirect('/fees_management')

    class_ = student['class']
    fees_data = load_fees_data(class_)

    if any(f['student_id'] == student_id and int(f['installment_no']) == installment_no for f in fees_data):
        return redirect(f'/fees_management?class={class_}&student={student_id}')

    if installment_no > 1:
        previous = next((f for f in fees_data if f['student_id'] == student_id and int(f['installment_no']) == installment_no - 1), None)
        if previous and datetime.strptime(date, '%Y-%m-%d') < datetime.strptime(previous['date'], '%Y-%m-%d'):
            return redirect(f'/fees_management?class={class_}&student={student_id}')

    total_fees = int(student['fees'])
    total_paid = sum(int(f['amount']) for f in fees_data if f['student_id'] == student_id)
    remaining = total_fees - total_paid
    if installment_no == int(student['installments']) and amount != remaining:
        return redirect(f'/fees_management?class={class_}&student={student_id}')
    if amount > remaining:
        return redirect(f'/fees_management?class={class_}&student={student_id}')

    fees_data.append({
        'student_id': student_id,
        'installment_no': str(installment_no),
        'amount': str(amount),
        'date': date
    })
    save_fees_data(class_, fees_data)

    return redirect(f'/fees_management?class={class_}&student={student_id}')

@app.route('/dashboard')
def dashboard():
    students = load_students()
    total_students = len(students)
    total_expected = sum(int(s['fees']) for s in students if s['fees'].isdigit())

    all_fees = []
    for class_name in set(s['class'] for s in students):
        all_fees += load_fees_data(class_name)

    total_collected = sum(int(f['amount']) for f in all_fees if f['amount'].isdigit())
    selected_month = request.args.get('month')
    month_students = []
    month_collected = 0

    if selected_month:
        y, m = map(int, selected_month.split('-'))
        for s in students:
            try:
                dt = datetime.strptime(s['admission_date'], '%Y-%m-%d')
                if dt.year == y and dt.month == m:
                    month_students.append(s)
            except:
                continue

        student_ids = {s['id'] for s in month_students}
        for f in all_fees:
            try:
                dt = datetime.strptime(f['date'], '%Y-%m-%d')
                if dt.year == y and dt.month == m and f['student_id'] in student_ids:
                    month_collected += int(f['amount'])
            except:
                continue

    months = set()
    for s in students:
        try:
            months.add(datetime.strptime(s['admission_date'], '%Y-%m-%d').strftime('%Y-%m'))
        except: pass
    for f in all_fees:
        try:
            months.add(datetime.strptime(f['date'], '%Y-%m-%d').strftime('%Y-%m'))
        except: pass

    return render_template('dashboard.html', total_students=total_students,
                           total_expected_fees=total_expected,
                           total_collected_fees=total_collected,
                           all_months=sorted(months),
                           selected_month=selected_month,
                           monthly_admissions=len(month_students),
                           monthly_fees_collected=month_collected,
                           admitted_students=[{'name': s['name'], 'class': s['class']} for s in month_students])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=700, debug=True)