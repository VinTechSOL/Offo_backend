from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd_context.hash("password123"))


#$2b$12$uPU1umlKqIi3Sh1R2mR1.Otc5T/Xm1IgW7RDWCzTIeuNTGhg5MHtm


'''

INSERT INTO core.roles (role_id, role_name) VALUES
(1, 'SUPER_ADMIN'),
(2, 'VENDOR_ADMIN'),
(3, 'STAFF');

INSERT INTO core.permissions (permission_id, permission_name) VALUES
(1, 'CREATE_CAFETERIA'),
(2, 'CREATE_BRANCH'),
(3, 'CREATE_MENU'),
(4, 'VIEW_ORDERS'),
(5, 'MANAGE_ORDERS'),
(6, 'VIEW_PAYMENTS');


-- SUPER ADMIN gets everything
INSERT INTO core.role_permissions (role_id, permission_id)
SELECT 1, permission_id FROM core.permissions;

-- VENDOR ADMIN
INSERT INTO core.role_permissions (role_id, permission_id) VALUES
(2, 3), -- CREATE_MENU
(2, 4), -- VIEW_ORDERS
(2, 5), -- MANAGE_ORDERS
(2, 6); -- VIEW_PAYMENTS

-- STAFF
INSERT INTO core.role_permissions (role_id, permission_id) VALUES
(3, 4), -- VIEW_ORDERS
(3, 5); -- MANAGE_ORDERS


INSERT INTO core.staff (
  staff_id,
  first_name,
  last_name,
  username,
  password_hash,
  role_id,
  branch_id,
  is_active
)
VALUES (
  1,
  'suraj',
  'singh',
  'vendor_admin_1',
  '$2b$12$uPU1umlKqIi3Sh1R2mR1.Otc5T/Xm1IgW7RDWCzTIeuNTGhg5MHtm',
  2,
  1,
  true
);



INSERT INTO core.staff (
  staff_id,
  first_name,
  last_name,
  username,
  password_hash,
  role_id,
  branch_id,
  is_active
)
VALUES (
  2,
  'Venkatesh',
  'Iyer',
  'vendor_1',
  '$2b$12$uPU1umlKqIi3Sh1R2mR1.Otc5T/Xm1IgW7RDWCzTIeuNTGhg5MHtm',
  3,
  1,
  true
);
'''