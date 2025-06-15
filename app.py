from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///bookstore.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

# 定义不区分大小写的替换过滤器
@app.template_filter('ireplace')
def ireplace(s, old, new):
    if not old or not new:
        return s
    return re.sub(re.escape(old), new, s, flags=re.IGNORECASE)


# 定义书籍模型
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100))
    category = db.Column(db.String(50))
    stock = db.Column(db.Integer)
    price = db.Column(db.Float)
    is_borrowable = db.Column(db.Boolean, default=True)

# 定义期刊模型
class Journal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    publisher = db.Column(db.String(100))
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)
    latest_issue = db.Column(db.String(20))
    category = db.Column(db.String(50))
    is_borrowable = db.Column(db.Boolean, default=True)

# 定义客户模型
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    membership_type = db.Column(db.String(20))
    registration_date = db.Column(db.DateTime, default=datetime.now)

# 定义销售记录模型
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(20))
    item_id = db.Column(db.Integer)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship('Customer', backref=db.backref('sales', lazy=True))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    total_price = db.Column(db.Float)
    sale_date = db.Column(db.DateTime, default=datetime.now)
    # 添加对 Book 和 Journal 的外键关联
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    book = db.relationship('Book', backref=db.backref('sales', lazy=True))
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'))
    journal = db.relationship('Journal', backref=db.backref('sales', lazy=True))

# 定义借阅记录模型
class Borrow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(20))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    book = db.relationship('Book', backref=db.backref('borrows', lazy=True))
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'))
    journal = db.relationship('Journal', backref=db.backref('borrows', lazy=True))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    customer = db.relationship('Customer', backref=db.backref('borrows', lazy=True))
    borrow_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='未归还')

# 首页
@app.route('/')
def index():
    book_count = Book.query.count()
    journal_count = Journal.query.count()
    customer_count = Customer.query.count()
    borrow_count = Borrow.query.filter_by(status='未归还').count()
    # 预加载关联对象
    recent_borrows = Borrow.query.options(
        db.joinedload(Borrow.book),
        db.joinedload(Borrow.journal),
        db.joinedload(Borrow.customer)
    ).order_by(Borrow.borrow_date.desc()).limit(5).all()
    recent_sales = Sale.query.options(
        db.joinedload(Sale.book),
        db.joinedload(Sale.journal),
        db.joinedload(Sale.customer)
    ).order_by(Sale.sale_date.desc()).limit(5).all()
    return render_template('index.html',
                           book_count=book_count,
                           journal_count=journal_count,
                           customer_count=customer_count,
                           borrow_count=borrow_count,
                           recent_borrows=recent_borrows,
                           recent_sales=recent_sales)

@app.route('/returns')
def returns():
    # 查询未归还的借阅记录
    borrows = Borrow.query.filter_by(status='未归还').all()
    return render_template('returns.html', borrows=borrows)

# 书籍管理
@app.route('/books', methods=['GET'])
def books():
    search_query = request.args.get('search', '').strip()

    # 基础查询
    query = Book.query

    # 应用搜索条件
    if search_query:
        query = query.filter(
            (Book.title.ilike(f'%{search_query}%')) |
            (Book.author.ilike(f'%{search_query}%')) |
            (Book.category.ilike(f'%{search_query}%'))
        )

    # 按书名排序
    books = query.order_by(Book.title).all()

    return render_template('books.html', books=books, search_query=search_query)

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        stock = int(request.form['stock'])
        price = float(request.form['price'])
        # 根据库存情况设置可借阅状态
        is_borrowable = stock > 0 and 'is_borrowable' in request.form
        new_book = Book(title=title, author=author, category=category, stock=stock, price=price,
                        is_borrowable=is_borrowable)
        db.session.add(new_book)
        db.session.commit()
        flash('书籍添加成功', 'success')
        return redirect(url_for('books'))
    return render_template('add_book.html')

@app.route('/edit_book/<int:id>', methods=['GET', 'POST'])
def edit_book(id):
    book = Book.query.get_or_404(id)
    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.category = request.form['category']
        book.stock = int(request.form['stock'])
        book.price = float(request.form['price'])
        # 根据库存情况设置可借阅状态
        book.is_borrowable = book.stock > 0 and 'is_borrowable' in request.form
        db.session.commit()
        flash('书籍信息更新成功', 'success')
        return redirect(url_for('books'))
    return render_template('edit_book.html', book=book)

@app.route('/delete_book/<int:id>')
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    flash('书籍删除成功', 'success')
    return redirect(url_for('books'))

# 期刊管理
@app.route('/journals', methods=['GET'])
def journals():
    search_query = request.args.get('search', '').strip()

    # 基础查询
    query = Journal.query

    # 应用搜索条件
    if search_query:
        query = query.filter(
            (Journal.title.ilike(f'%{search_query}%')) |
            (Journal.publisher.ilike(f'%{search_query}%')) |
            (Journal.category.ilike(f'%{search_query}%')) |
            (Journal.latest_issue.ilike(f'%{search_query}%'))
        )

    # 按期刊名排序
    journals = query.order_by(Journal.title).all()

    return render_template('journals.html', journals=journals, search_query=search_query)

@app.route('/add_journal', methods=['GET', 'POST'])
def add_journal():
    if request.method == 'POST':
        title = request.form['title']
        publisher = request.form['publisher']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        latest_issue = request.form['latest_issue']
        category = request.form.get('category')  # 确认获取类别数据
        is_borrowable = 'is_borrowable' in request.form
        new_journal = Journal(title=title, publisher=publisher, price=price, stock=stock,
                              latest_issue=latest_issue, category=category, is_borrowable=is_borrowable)
        db.session.add(new_journal)
        db.session.commit()
        flash('期刊添加成功', 'success')
        return redirect(url_for('journals'))
    return render_template('add_journal.html')

@app.route('/edit_journal/<int:id>', methods=['GET', 'POST'])
def edit_journal(id):
    journal = Journal.query.get_or_404(id)
    if request.method == 'POST':
        journal.title = request.form['title']
        journal.publisher = request.form['publisher']
        journal.price = float(request.form['price'])
        journal.stock = int(request.form['stock'])
        journal.latest_issue = request.form['latest_issue']
        journal.is_borrowable = 'is_borrowable' in request.form
        db.session.commit()
        flash('期刊信息更新成功', 'success')
        return redirect(url_for('journals'))
    return render_template('edit_journal.html', journal=journal)

@app.route('/delete_journal/<int:id>')
def delete_journal(id):
    journal = Journal.query.get_or_404(id)
    db.session.delete(journal)
    db.session.commit()
    flash('期刊删除成功', 'success')
    return redirect(url_for('journals'))

# 客户管理
@app.route('/customers', methods=['GET'])
def customers():
    search = request.args.get('search', '').strip()  # 获取搜索参数并去除两端空格
    if search:
        customers = Customer.query.filter(
            (Customer.name.contains(search)) |
            (Customer.phone.contains(search)) |
            (Customer.email.contains(search))
        ).all()
    else:
        customers = Customer.query.all()
    return render_template('customers.html', customers=customers, search_query=search)

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']  # 获取电邮信息
        address = request.form['address']  # 获取地址信息
        membership_type = request.form['membership_type']
        new_customer = Customer(name=name, phone=phone, email=email, address=address, membership_type=membership_type)
        db.session.add(new_customer)
        db.session.commit()
        flash('客户添加成功', 'success')
        return redirect(url_for('customers'))
    return render_template('add_customer.html')

@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.phone = request.form['phone']
        customer.email = request.form['email']  # 更新电邮信息
        customer.address = request.form['address']  # 更新地址信息
        customer.membership_type = request.form['membership_type']
        db.session.commit()
        flash('客户信息更新成功', 'success')
        return redirect(url_for('customers'))
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete_customer/<int:id>')
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('客户删除成功', 'success')
    return redirect(url_for('customers'))

# 销售管理
@app.route('/sales', methods=['GET'])
def sales():
    search_query = request.args.get('search', '').strip()

    # 基础查询，预加载关联对象
    query = Sale.query.options(
        db.joinedload(Sale.book),
        db.joinedload(Sale.journal),
        db.joinedload(Sale.customer)
    ).order_by(Sale.sale_date.desc())

    # 应用搜索条件
    if search_query:
        # 按商品名称搜索（书籍或期刊）
        book_condition = db.and_(
            Sale.item_type == 'book',
            Book.title.ilike(f'%{search_query}%')
        )

        journal_condition = db.and_(
            Sale.item_type == 'journal',
            Journal.title.ilike(f'%{search_query}%')
        )

        # 按客户名称搜索
        customer_condition = Customer.name.ilike(f'%{search_query}%')

        # 按销售日期搜索
        date_condition = db.func.strftime('%Y-%m-%d', Sale.sale_date).ilike(f'%{search_query}%')

        # 组合所有搜索条件
        query = query.join(Sale.customer, isouter=True).filter(
            db.or_(
                book_condition,
                journal_condition,
                customer_condition,
                date_condition
            )
        )

    sales = query.all()
    return render_template('sales.html', sales=sales, search_query=search_query)

@app.route('/add_sale', methods=['GET', 'POST'])
def add_sale():
    # 获取所有客户用于下拉选择
    customers = Customer.query.all()

    if request.method == 'POST':
        item_type = request.form['item_type']
        item_id = int(request.form['item_id'])
        customer_id = int(request.form['customer_id'])  # 获取客户ID
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        total_price = float(request.form['total_price'])

        if item_type == 'book':
            book = Book.query.get(item_id)
            if book and book.stock >= quantity:
                new_sale = Sale(
                    item_type=item_type,
                    item_id=item_id,
                    customer_id=customer_id,  # 关联客户ID
                    quantity=quantity,
                    price=price,
                    total_price=total_price,
                    book=book,
                    book_id=item_id
                )
                book.stock -= quantity
            else:
                flash('书籍库存不足，无法销售', 'error')
                return redirect(url_for('add_sale'))
        elif item_type == 'journal':
            journal = Journal.query.get(item_id)
            if journal and journal.stock >= quantity:
                new_sale = Sale(
                    item_type=item_type,
                    item_id=item_id,
                    customer_id=customer_id,  # 关联客户ID
                    quantity=quantity,
                    price=price,
                    total_price=total_price,
                    journal=journal,
                    journal_id=item_id
                )
                journal.stock -= quantity
            else:
                flash('期刊库存不足，无法销售', 'error')
                return redirect(url_for('add_sale'))

        db.session.add(new_sale)
        db.session.commit()
        flash('销售记录添加成功', 'success')
        return redirect(url_for('sales'))

    # 获取书籍和期刊列表（若有需要）
    books = Book.query.all()
    journals = Journal.query.all()
    return render_template('add_sale.html', customers=customers, books=books, journals=journals)

@app.route('/get_items_by_type/<type>')
def get_items_by_type(type):
    if type == 'book':
        items = Book.query.all()
    elif type == 'journal':
        items = Journal.query.all()
    else:
        return jsonify([])

    item_list = []
    for item in items:
        item_list.append({
            'id': item.id,
            'name': item.title,
            'stock': item.stock
        })
    return jsonify(item_list)


@app.route('/delete_sale/<int:id>')
def delete_sale(id):
    sale = Sale.query.get_or_404(id)

    # 恢复库存
    if sale.item_type == 'book' and sale.book:
        sale.book.stock += sale.quantity
    elif sale.item_type == 'journal' and sale.journal:
        sale.journal.stock += sale.quantity

    db.session.delete(sale)
    db.session.commit()
    flash('销售记录删除成功，库存已恢复', 'success')
    return redirect(url_for('sales'))

# 借阅管理
@app.route('/borrows')
def borrows():
    search_query = request.args.get('search', '').strip()

    # 基础查询
    query = Borrow.query

    # 简单搜索实现（仅匹配书籍标题和客户姓名）
    if search_query:
        query = query.filter(
            (Borrow.book.has(Book.title.ilike(f'%{search_query}%'))) |
            (Borrow.customer.has(Customer.name.ilike(f'%{search_query}%')))
        )

    # 简单分页（默认显示全部记录，可通过page参数分页）
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 每页显示20条
    borrows = query.order_by(Borrow.borrow_date.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template('borrows.html', borrows=borrows, search_query=search_query, datetime=datetime)

# 添加借阅记录
@app.route('/add_borrow', methods=['GET', 'POST'])
def add_borrow():
    if request.method == 'POST':
        item_type = request.form['item_type']
        book_id = int(request.form['book_id']) if item_type == 'book' else None
        journal_id = int(request.form['journal_id']) if item_type == 'journal' else None
        customer_id = int(request.form['customer_id'])
        due_date_str = request.form['due_date']
        # 将 due_date 从字符串转换为 datetime 对象
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        # 手动设置 borrow_date
        borrow_date = datetime.now()

        new_borrow = Borrow(
            item_type=item_type,
            book_id=book_id,
            journal_id=journal_id,
            customer_id=customer_id,
            borrow_date=borrow_date,
            due_date=due_date
        )

        try:
            if item_type == 'book':
                book = Book.query.get(book_id)
                if book.stock > 0:
                    book.stock -= 1
                else:
                    flash('书籍库存不足，无法借阅', 'error')
                    return redirect(url_for('add_borrow'))
            elif item_type == 'journal':
                journal = Journal.query.get(journal_id)
                if journal.stock > 0:
                    journal.stock -= 1
                else:
                    flash('期刊库存不足，无法借阅', 'error')
                    return redirect(url_for('add_borrow'))

            db.session.add(new_borrow)
            db.session.commit()
            flash('借阅记录添加成功', 'success')
            return redirect(url_for('borrows'))
        except Exception as e:
            db.session.rollback()
            flash(f'借阅记录添加失败: {str(e)}', 'error')

    books = Book.query.all()
    journals = Journal.query.all()
    customers = Customer.query.all()
    return render_template('add_borrow.html', books=books, journals=journals, customers=customers)


@app.route('/process_return/<int:id>', methods=['POST'])
def process_return(id):
    borrow = Borrow.query.get_or_404(id)
    if borrow.status == '未归还':
        # 更新借阅记录状态和归还日期
        borrow.return_date = datetime.now()
        borrow.status = '已归还'
        # 更新书籍或期刊库存
        if borrow.item_type == 'book' and borrow.book:
            borrow.book.stock += 1
        elif borrow.item_type == 'journal' and borrow.journal:
            borrow.journal.stock += 1
        try:
            db.session.commit()
            flash('归还处理成功', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'归还处理失败: {str(e)}', 'error')
    else:
        flash('该借阅记录已处理过归还', 'warning')
    return redirect(url_for('borrows'))

@app.route('/delete_borrow/<int:id>')
def delete_borrow(id):
    borrow = Borrow.query.get_or_404(id)
    try:
        if borrow.status == '未归还':
            # 如果借阅未归还，归还书籍或期刊库存
            if borrow.item_type == 'book' and borrow.book:
                borrow.book.stock += 1
            elif borrow.item_type == 'journal' and borrow.journal:
                borrow.journal.stock += 1
        # 删除借阅记录
        db.session.delete(borrow)
        db.session.commit()
        flash('借阅记录删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'借阅记录删除失败: {str(e)}', 'error')
    return redirect(url_for('borrows'))

# 统计信息
@app.route('/statistics')
def statistics():
    book_count = Book.query.count()
    journal_count = Journal.query.count()
    customer_count = Customer.query.count()
    total_sales = Sale.query.count()
    # 计算总借阅数
    total_borrows = Borrow.query.count()

    return render_template('statistics.html',
                           book_count=book_count,
                           journal_count=journal_count,
                           customer_count=customer_count,
                           total_sales=total_sales,
                           total_borrows=total_borrows)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)