"""
Entity Correlation Tool for CrewAI
Correlates data across multiple entities (customers, bills, payments)
"""

import json
from typing import Dict, Any, List
from crewai.tools import BaseTool


class EntityCorrelatorTool(BaseTool):
    name: str = "entity_correlator"
    description: str = "Correlate data across multiple entities (customers, bills, payments) to provide comprehensive results"
    
    def _run(self, query_results: str, correlation_type: str = "customer_bills_payments", **kwargs) -> str:
        """
        Correlate data across multiple entities
        
        Args:
            query_results: JSON string containing results from multiple entity queries
            correlation_type: Type of correlation to perform
        
        Returns:
            JSON string with correlated results
        """
        try:
            results = json.loads(query_results)
            
            if correlation_type == "customer_bills_payments":
                return self._correlate_customer_bills_payments(results)
            elif correlation_type == "account_payments":
                return self._correlate_account_payments(results)
            else:
                return json.dumps({"error": f"Unknown correlation type: {correlation_type}"})
                
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def _correlate_customer_bills_payments(self, results: Dict[str, Any]) -> str:
        """Correlate customers with their bills and payments"""
        try:
            # Extract data from results
            customers = results.get('data', {}).get('list_customers', [])
            bills = results.get('data', {}).get('list_bills', [])
            payments = results.get('data', {}).get('list_payments', [])
            
            # Create lookup maps
            customer_map = {c.get('customer_id'): c for c in customers}
            bill_map = {b.get('bill_id'): b for b in bills}
            
            # Group payments by account_id
            payments_by_account = {}
            for payment in payments:
                account_id = payment.get('account_id')
                if account_id not in payments_by_account:
                    payments_by_account[account_id] = []
                payments_by_account[account_id].append(payment)
            
            # Group bills by account_id
            bills_by_account = {}
            for bill in bills:
                account_id = bill.get('account_id')
                if account_id not in bills_by_account:
                    bills_by_account[account_id] = []
                bills_by_account[account_id].append(bill)
            
            # Correlate data
            correlated_results = []
            
            for customer in customers:
                customer_id = customer.get('customer_id')
                customer_data = {
                    'customer': customer,
                    'accounts': [],
                    'total_bills': 0,
                    'total_payments': 0,
                    'unpaid_bills': 0,
                    'total_amount_due': 0,
                    'total_payments_amount': 0
                }
                
                # Find accounts for this customer (assuming customer_id matches account_id pattern)
                # This is a simplified correlation - in real scenario, you'd have a proper relationship
                for account_id in payments_by_account.keys():
                    if customer_id in account_id or account_id in customer_id:
                        account_data = {
                            'account_id': account_id,
                            'bills': bills_by_account.get(account_id, []),
                            'payments': payments_by_account.get(account_id, [])
                        }
                        
                        # Calculate totals
                        account_data['total_bills'] = len(account_data['bills'])
                        account_data['total_payments'] = len(account_data['payments'])
                        account_data['unpaid_bills'] = len([b for b in account_data['bills'] if b.get('status') == 'UNPAID'])
                        account_data['total_amount_due'] = sum(float(b.get('amount_due', 0)) for b in account_data['bills'] if b.get('status') == 'UNPAID')
                        account_data['total_payments_amount'] = sum(float(p.get('amount', 0)) for p in account_data['payments'])
                        
                        customer_data['accounts'].append(account_data)
                        customer_data['total_bills'] += account_data['total_bills']
                        customer_data['total_payments'] += account_data['total_payments']
                        customer_data['unpaid_bills'] += account_data['unpaid_bills']
                        customer_data['total_amount_due'] += account_data['total_amount_due']
                        customer_data['total_payments_amount'] += account_data['total_payments_amount']
                
                correlated_results.append(customer_data)
            
            return json.dumps({
                'correlated_data': correlated_results,
                'summary': {
                    'total_customers': len(correlated_results),
                    'customers_with_unpaid_bills': len([c for c in correlated_results if c['unpaid_bills'] > 0]),
                    'total_unpaid_amount': sum(c['total_amount_due'] for c in correlated_results)
                }
            })
            
        except Exception as e:
            return json.dumps({"error": f"Correlation failed: {str(e)}"})
    
    def _correlate_account_payments(self, results: Dict[str, Any]) -> str:
        """Correlate accounts with their payments"""
        try:
            payments = results.get('data', {}).get('list_payments', [])
            
            # Group payments by account_id
            payments_by_account = {}
            for payment in payments:
                account_id = payment.get('account_id')
                if account_id not in payments_by_account:
                    payments_by_account[account_id] = []
                payments_by_account[account_id].append(payment)
            
            # Create account summaries
            account_summaries = []
            for account_id, account_payments in payments_by_account.items():
                summary = {
                    'account_id': account_id,
                    'total_payments': len(account_payments),
                    'total_amount': sum(float(p.get('amount', 0)) for p in account_payments),
                    'successful_payments': len([p for p in account_payments if p.get('status') == 'POSTED']),
                    'failed_payments': len([p for p in account_payments if p.get('status') == 'FAILED']),
                    'payments': account_payments
                }
                account_summaries.append(summary)
            
            return json.dumps({
                'account_summaries': account_summaries,
                'summary': {
                    'total_accounts': len(account_summaries),
                    'total_payments': sum(s['total_payments'] for s in account_summaries),
                    'total_amount': sum(s['total_amount'] for s in account_summaries)
                }
            })
            
        except Exception as e:
            return json.dumps({"error": f"Account correlation failed: {str(e)}"})
