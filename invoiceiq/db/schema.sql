CREATE TABLE IF NOT EXISTS vendors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  gstin VARCHAR(32),
  rating DECIMAL(4,2),
  risk_score DECIMAL(5,2) DEFAULT 0
);
CREATE TABLE IF NOT EXISTS invoices (
  id INT AUTO_INCREMENT PRIMARY KEY,
  supplier_name VARCHAR(255),
  supplier_gstin VARCHAR(32),
  invoice_no VARCHAR(64),
  invoice_date DATE,
  subtotal DECIMAL(12,2),
  tax DECIMAL(12,2),
  total DECIMAL(12,2),
  status ENUM('PENDING','APPROVED') DEFAULT 'PENDING',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS invoice_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  invoice_id INT NOT NULL,
  sku VARCHAR(64),
  description VARCHAR(255),
  qty DECIMAL(12,2),
  unit_price DECIMAL(12,2),
  tax_rate DECIMAL(5,2),
  line_total DECIMAL(12,2),
  FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
CREATE INDEX idx_invoices_gstin_date ON invoices (supplier_gstin, invoice_date);
CREATE INDEX idx_items_sku ON invoice_items (sku);
