-- 书店管理系统数据库结构

-- 创建分类表
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- 创建出版社表
CREATE TABLE publishers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(200),
    phone VARCHAR(20),
    email VARCHAR(100)
);

-- 创建书籍表
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    price DECIMAL(10, 2) NOT NULL,
    total_quantity INT NOT NULL,
    available_quantity INT NOT NULL,
    unit VARCHAR(10) NOT NULL CHECK (unit = '本'),
    publication_date DATE NOT NULL,
    category_id INT NOT NULL,
    publisher_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (publisher_id) REFERENCES publishers(id)
);

-- 创建期刊表
CREATE TABLE journals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    issn VARCHAR(20) NOT NULL UNIQUE,
    volume INT NOT NULL,
    issue INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    total_quantity INT NOT NULL,
    available_quantity INT NOT NULL,
    unit VARCHAR(10) NOT NULL CHECK (unit = '本'),
    publication_date DATE NOT NULL,
    category_id INT NOT NULL,
    publisher_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (publisher_id) REFERENCES publishers(id)
);

-- 创建客户表
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    gender VARCHAR(10),
    birth_date DATE,
    phone VARCHAR(20),
    address VARCHAR(200),
    email VARCHAR(100),
    registration_date DATE NOT NULL DEFAULT (CURRENT_DATE()),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建借阅记录表
CREATE TABLE borrows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT,
    journal_id INT,
    customer_id INT NOT NULL,
    borrow_date DATE NOT NULL,
    due_date DATE NOT NULL,
    returned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (journal_id) REFERENCES journals(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- 创建归还记录表
CREATE TABLE returns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    borrow_id INT NOT NULL UNIQUE,
    return_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (borrow_id) REFERENCES borrows(id)
);

-- 创建销售记录表
CREATE TABLE sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT,
    journal_id INT,
    quantity INT NOT NULL,
    sale_date DATE NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (journal_id) REFERENCES journals(id)
);

-- 创建触发器：更新书籍和期刊库存（借阅归还）
DELIMITER $$

CREATE TRIGGER update_stock_on_borrow_return_trigger
AFTER UPDATE ON borrows
FOR EACH ROW
BEGIN
    IF NEW.returned = TRUE AND OLD.returned = FALSE THEN
        IF NEW.book_id IS NOT NULL THEN
            UPDATE books
            SET available_quantity = available_quantity + 1
            WHERE id = NEW.book_id;
        ELSEIF NEW.journal_id IS NOT NULL THEN
            UPDATE journals
            SET available_quantity = available_quantity + 1
            WHERE id = NEW.journal_id;
        END IF;
    ELSEIF NEW.returned = FALSE AND OLD.returned = TRUE THEN
        IF NEW.book_id IS NOT NULL THEN
            UPDATE books
            SET available_quantity = available_quantity - 1
            WHERE id = NEW.book_id;
        ELSEIF NEW.journal_id IS NOT NULL THEN
            UPDATE journals
            SET available_quantity = available_quantity - 1
            WHERE id = NEW.journal_id;
        END IF;
    END IF;
END$$

DELIMITER ;

-- 创建触发器：销售时减少库存
DELIMITER $$

CREATE TRIGGER reduce_stock_on_sale_trigger
AFTER INSERT ON sales
FOR EACH ROW
BEGIN
    IF NEW.book_id IS NOT NULL THEN
        UPDATE books
        SET available_quantity = available_quantity - NEW.quantity
        WHERE id = NEW.book_id;
    ELSEIF NEW.journal_id IS NOT NULL THEN
        UPDATE journals
        SET available_quantity = available_quantity - NEW.quantity
        WHERE id = NEW.journal_id;
    END IF;
END$$

DELIMITER ;

-- 创建触发器：检查借阅时库存是否充足
DELIMITER $$

CREATE TRIGGER check_stock_on_borrow_trigger
BEFORE INSERT ON borrows
FOR EACH ROW
BEGIN
    DECLARE current_stock INT;
    IF NEW.book_id IS NOT NULL THEN
        SELECT available_quantity INTO current_stock FROM books WHERE id = NEW.book_id;
    ELSEIF NEW.journal_id IS NOT NULL THEN
        SELECT available_quantity INTO current_stock FROM journals WHERE id = NEW.journal_id;
    END IF;
    IF current_stock <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '库存不足，无法借阅';
    END IF;
END$$

DELIMITER ;

-- 创建触发器：检查销售时库存是否充足
DELIMITER $$

CREATE TRIGGER check_stock_on_sale_trigger
BEFORE INSERT ON sales
FOR EACH ROW
BEGIN
    DECLARE current_stock INT;
    IF NEW.book_id IS NOT NULL THEN
        SELECT available_quantity INTO current_stock FROM books WHERE id = NEW.book_id;
    ELSEIF NEW.journal_id IS NOT NULL THEN
        SELECT available_quantity INTO current_stock FROM journals WHERE id = NEW.journal_id;
    END IF;
    IF current_stock < NEW.quantity THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '库存不足，无法销售';
    END IF;
END$$

DELIMITER ;

-- 创建视图：当前借阅情况
CREATE VIEW current_borrows AS
SELECT
    b.id,
    COALESCE(bo.title, j.title) AS item_title,
    c.name AS customer_name,
    c.phone AS customer_phone,
    b.borrow_date,
    b.due_date,
    b.returned
FROM
    borrows b
LEFT JOIN
    books bo ON b.book_id = bo.id
LEFT JOIN
    journals j ON b.journal_id = j.id
JOIN
    customers c ON b.customer_id = c.id
WHERE
    b.returned = FALSE;

-- 创建视图：销售统计
CREATE VIEW sales_statistics AS
SELECT
    DATE(s.sale_date) AS sale_day,
    CASE
        WHEN s.book_id IS NOT NULL THEN 'book'
        WHEN s.journal_id IS NOT NULL THEN 'journal'
    END AS item_type,
    COUNT(*) AS transactions,
    SUM(s.quantity) AS total_quantity,
    SUM(s.price * s.quantity) AS total_amount
FROM
    sales s
GROUP BY
    DATE(s.sale_date),
    CASE
        WHEN s.book_id IS NOT NULL THEN 'book'
        WHEN s.journal_id IS NOT NULL THEN 'journal'
    END
ORDER BY
    sale_day DESC;

-- 创建视图：库存状态
CREATE VIEW inventory_status AS
SELECT
    'book' AS item_type,
    b.id,
    b.title,
    c.name AS category,
    b.available_quantity,
    b.price
FROM
    books b
JOIN
    categories c ON b.category_id = c.id
UNION ALL
SELECT
    'journal' AS item_type,
    j.id,
    j.title,
    c.name AS category,
    j.available_quantity,
    j.price
FROM
    journals j
JOIN
    categories c ON j.category_id = c.id;