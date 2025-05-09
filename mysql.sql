-- 1. Users Table
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE
);

-- 2. Books Table
CREATE TABLE books (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(100) NOT NULL,
    author VARCHAR(100),
    price DECIMAL(10, 2),
    stock INT DEFAULT 0
);

-- 3. Orders Table
CREATE TABLE orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 4. Order Items Table
CREATE TABLE order_items (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    id INT,
    quantity INT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (id) REFERENCES books(id)
);

-- Assertions

-- Assertion 1: Book price must be positive
ALTER TABLE books ADD CONSTRAINT price_check CHECK (price > 0);

-- Assertion 2: Quantity of order items must be positive
ALTER TABLE order_items ADD CONSTRAINT quantity_check CHECK (quantity > 0);

-- Triggers
DELIMITER $$
CREATE TRIGGER decrease_stock
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
  UPDATE books
  SET stock = stock - NEW.quantity
  WHERE id = NEW.id;
END;$$

CREATE TRIGGER prevent_out_of_stock
BEFORE INSERT ON order_items
FOR EACH ROW
BEGIN
  DECLARE available_stock INT;

  SELECT stock INTO available_stock
  FROM books
  WHERE id = NEW.book_id;

  IF available_stock < NEW.quantity THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Not enough stock available';
  END IF;
END;$$
DELIMITER ;

