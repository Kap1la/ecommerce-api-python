An headless commerce api in python using postgres.

Design decisions:
- Admins create new customer accounts, not the customers themselves.
    - The customer accounts aren't directly to be operated by the customers, but rather reflect the customer's actions.
    - e.g. When a customer first places an order, if its details are valid, it's status is set as pending.
        - Then, the customer can choose to have the order 'cancelled' or 'confirmed', 




if pending restock order with that product exists, and deactivation of that product is requested sans force, the deactivation will not happen. If forced, the restock order items referencing that product will be deleted and any empty restock orders will be cancelled.

A pending order, logically, is one that has yet to be paid for/finalized. So, force deactivate modifying pending orders of any sort makes 


Sales order lifecycle:
Customer-type user makes order, if order details as valid, status is set as 'pending'