INSERT INTO vendors (name, gstin, rating, risk_score) VALUES
 ('Acme Supplies','29ABCDE1234F1Z5',4.5,12.0),
 ('Globex Retail','27PQRSX9876L1Z3',4.1,8.0);
INSERT INTO invoices (supplier_name, supplier_gstin, invoice_no, invoice_date, subtotal, tax, total, status)
VALUES ('Acme Supplies','29ABCDE1234F1Z5','INV-1001','2025-10-01',10000,1800,11800,'APPROVED');
INSERT INTO invoice_items (invoice_id, sku, description, qty, unit_price, tax_rate, line_total)
VALUES (1,'SKU-RED-PEN','Red Pen',100,50,18,5900),
       (1,'SKU-NOTE-A5','A5 Notebook',50,100,18,5900);
