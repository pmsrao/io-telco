"""
Query Builder Tools for CrewAI
Builds GraphQL queries from contracts and user intent
"""

import json
import re
from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool


class GraphQLQueryBuilderTool(BaseTool):
    name: str = "graphql_query_builder"
    description: str = "Build GraphQL queries from user intent and contract information"
    
    def _run(self, intent: str, contract_data: str = None, schema_data: str = None, **kwargs) -> str:
        """
        Build a GraphQL query from user intent and contract data
        
        Args:
            intent: User's natural language intent
            contract_data: JSON string with contract information
            schema_data: Optional GraphQL schema data
        
        Returns:
            JSON string with the built GraphQL query and variables
        """
        try:
            # Handle different input formats from CrewAI
            if isinstance(intent, dict):
                intent = intent.get('intent', 'show me data')
                contract_data = intent.get('contract_data', '{}')
                schema_data = intent.get('schema_data', '')
            
            # Ensure all parameters are strings
            if not isinstance(intent, str):
                intent = str(intent)
            if not isinstance(contract_data, str):
                contract_data = str(contract_data) if contract_data else '{}'
            if not isinstance(schema_data, str):
                schema_data = str(schema_data) if schema_data else ''
            if schema_data is None:
                schema_data = ''
            
            # Handle different contract data formats
            if not contract_data or contract_data == '{}':
                contract_data = '{"entities": {"payments": {"aliases": ["list_payments"], "columns": {"payment_id": "String", "amount": "Decimal", "status": "String", "created_at": "Timestamp"}}}}'
            elif '"product"' in contract_data:
                # Convert product format to full contract format
                try:
                    product_data = json.loads(contract_data)
                    product_name = product_data.get('product', 'payments')
                    contract_data = f'{{"entities": {{"{product_name}": {{"aliases": ["list_{product_name}"], "columns": {{"id": "String", "amount": "Decimal", "status": "String", "created_at": "Timestamp"}}}}}}}}'
                except json.JSONDecodeError:
                    # If JSON parsing fails, use default
                    contract_data = '{"entities": {"payments": {"aliases": ["list_payments"], "columns": {"payment_id": "String", "amount": "Decimal", "status": "String", "created_at": "Timestamp"}}}}'
            
            # Try to parse contract data, with fallback
            try:
                contract = json.loads(contract_data)
            except json.JSONDecodeError as e:
                # If parsing fails, create a simple default contract
                print(f"JSON parsing error: {e}")
                print(f"Contract data: {contract_data[:200]}...")
                contract = {
                    "entities": {
                        "payments": {
                            "aliases": ["list_payments"],
                            "columns": {
                                "payment_id": "String",
                                "account_id": "String", 
                                "amount": "Decimal",
                                "status": "String",
                                "created_at": "Timestamp"
                            }
                        }
                    }
                }
            
            # Parse intent to extract key information
            intent_info = self._parse_intent(intent)
            
            # Check if this is a multi-entity query
            entities = intent_info.get('entities', [])
            if len(entities) > 1:
                # Multi-entity queries should use the simple query builder
                return self._build_simple_query(intent_info)
            
            # Find matching operations from contract
            operations = self._find_matching_operations(intent_info, contract)
            
            if not operations:
                # Fallback: build a simple query directly
                return self._build_simple_query(intent_info)
            
            # Build GraphQL query
            query_result = self._build_query(intent_info, operations[0], contract)
            
            return json.dumps(query_result)
            
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def _parse_intent(self, intent: str) -> Dict[str, Any]:
        """Parse user intent to extract key information"""
        intent_lower = intent.lower()
        
        # Extract entity types with better pattern matching
        entities = []
        if any(word in intent_lower for word in ['payment', 'payments', 'payment history']):
            entities.append('payments')
        if any(word in intent_lower for word in ['bill', 'bills', 'unpaid bills', 'unpaid bill']):
            entities.append('bills')
        if any(word in intent_lower for word in ['customer', 'customers', 'all customers']):
            entities.append('customer_profile')
        if any(word in intent_lower for word in ['account', 'accounts']):
            entities.append('customer_accounts')
        if any(word in intent_lower for word in ['subscription', 'subscriptions']):
            entities.append('customer_subscriptions')
        
        # For complex queries, try to infer multiple entities
        if 'and' in intent_lower or 'with' in intent_lower:
            # If query mentions multiple concepts, include relevant entities
            if 'customer' in intent_lower and 'payment' in intent_lower:
                if 'customer_profile' not in entities:
                    entities.append('customer_profile')
                if 'payments' not in entities:
                    entities.append('payments')
            if 'customer' in intent_lower and 'bill' in intent_lower:
                if 'customer_profile' not in entities:
                    entities.append('customer_profile')
                if 'bills' not in entities:
                    entities.append('bills')
            if 'bill' in intent_lower and 'payment' in intent_lower:
                if 'bills' not in entities:
                    entities.append('bills')
                if 'payments' not in entities:
                    entities.append('payments')
        
        # If no entities found, default to payments for general queries
        if not entities:
            entities.append('payments')
        
        # Extract action types
        actions = []
        if any(word in intent_lower for word in ['show', 'list', 'get', 'find', 'search']):
            actions.append('list')
        if any(word in intent_lower for word in ['get', 'fetch', 'retrieve']):
            actions.append('get')
        
        # If no actions found, default to list
        if not actions:
            actions.append('list')
        
        # Extract filters
        filters = {}
        
        # Account ID
        account_match = re.search(r'acc[_-]?(\d+)', intent_lower)
        if account_match:
            filters['account_id'] = f"ACC-{account_match.group(1)}"
        
        # Also look for "for account" pattern
        account_for_match = re.search(r'for account\s+([a-zA-Z0-9_-]+)', intent_lower)
        if account_for_match:
            filters['account_id'] = account_for_match.group(1)
        
        # Bill ID
        bill_match = re.search(r'bill[_-]?(\d+)', intent_lower)
        if bill_match:
            filters['bill_id'] = f"BILL-{bill_match.group(1)}"
        
        # Geographic filters
        country_match = re.search(r'\bin\s+([a-zA-Z]+)', intent_lower)
        if country_match:
            country = country_match.group(1).title()
            # Map country names to country codes
            country_mapping = {
                'India': 'IN',
                'United States': 'US',
                'United Arab Emirates': 'AE',
                'UAE': 'AE'
            }
            filters['country'] = country_mapping.get(country, country)
        
        # Status filters with better pattern matching
        if any(word in intent_lower for word in ['posted', 'paid', 'successful']):
            filters['status'] = 'POSTED'
        elif any(word in intent_lower for word in ['failed', 'failure', 'error']):
            filters['status'] = 'FAILED'
        elif any(word in intent_lower for word in ['open', 'pending', 'unpaid']):
            filters['status'] = 'OPEN'
        elif any(word in intent_lower for word in ['unpaid bills', 'unpaid bill']):
            filters['bill_status'] = 'UNPAID'
        
        # Bill status filters
        if any(word in intent_lower for word in ['unpaid', 'overdue', 'due']):
            filters['bill_status'] = 'UNPAID'
        elif any(word in intent_lower for word in ['paid bills', 'paid bill']):
            filters['bill_status'] = 'PAID'
        
        # Time ranges
        if 'last 30 days' in intent_lower:
            filters['time_range'] = 'last_30_days'
        elif 'last week' in intent_lower:
            filters['time_range'] = 'last_week'
        elif 'last month' in intent_lower:
            filters['time_range'] = 'last_month'
        
        return {
            'entities': entities,
            'actions': actions,
            'filters': filters,
            'original_intent': intent
        }
    
    def _find_matching_operations(self, intent_info: Dict[str, Any], contract: Dict[str, Any]) -> List[str]:
        """Find operations that match the user intent"""
        entities = intent_info.get('entities', [])
        actions = intent_info.get('actions', [])
        
        matching_operations = []
        
        # Get available aliases from contract
        available_aliases = []
        for entity_name, entity_data in contract.get('entities', {}).items():
            aliases = entity_data.get('aliases', [])
            available_aliases.extend(aliases)
        
        # Match based on entities and actions
        for alias in available_aliases:
            alias_lower = alias.lower()
            
            # Check if alias matches any of the entities
            entity_match = any(entity in alias_lower for entity in entities)
            
            # Check if alias matches any of the actions
            action_match = any(action in alias_lower for action in actions)
            
            if entity_match and action_match:
                matching_operations.append(alias)
        
        return matching_operations
    
    def _build_query(self, intent_info: Dict[str, Any], operation: str, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Build the actual GraphQL query"""
        filters = intent_info.get('filters', {})
        
        # Build variables
        variables = {}
        filter_args = []
        
        # Add time range variables if specified
        if 'time_range' in filters:
            from datetime import datetime, timedelta
            
            now = datetime.now()
            if filters['time_range'] == 'last_30_days':
                from_time = now - timedelta(days=30)
            elif filters['time_range'] == 'last_week':
                from_time = now - timedelta(days=7)
            elif filters['time_range'] == 'last_month':
                from_time = now - timedelta(days=30)
            else:
                from_time = now - timedelta(days=30)
            
            variables['from_time'] = from_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            variables['to_time'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')
            filter_args.append('from_time: $from_time')
            filter_args.append('to_time: $to_time')
        
        # Add other filters
        for filter_name, filter_value in filters.items():
            if filter_name == 'time_range':
                continue
            
            var_name = filter_name
            variables[var_name] = filter_value
            filter_args.append(f'{filter_name}: ${var_name}')
        
        # Build the query string
        if filter_args:
            filters_str = f"filters: {{ {', '.join(filter_args)} }}"
        else:
            filters_str = ""
        
        # Determine if it's a list or get operation
        if operation.startswith('list_'):
            query = f"""
            query {operation}({', '.join(f'${var}: String!' for var in variables.keys())}) {{
                {operation}({filters_str}, limit: 50) {{
                    {self._get_fields_for_operation(operation, contract)}
                }}
            }}
            """
        else:
            # For get operations, we need a key
            key_var = 'key'
            variables[key_var] = filters.get('bill_id') or filters.get('account_id') or 'UNKNOWN'
            query = f"""
            query {operation}(${key_var}: String!) {{
                {operation}(key: ${key_var}) {{
                    {self._get_fields_for_operation(operation, contract)}
                }}
            }}
            """
        
        return {
            'query': query.strip(),
            'variables': variables
        }
    
    def _get_fields_for_operation(self, operation: str, contract: Dict[str, Any]) -> str:
        """Get the fields to select for a given operation"""
        # Find the entity this operation belongs to
        for entity_name, entity_data in contract.get('entities', {}).items():
            aliases = entity_data.get('aliases', [])
            if operation in aliases:
                # Get the columns for this entity
                columns = entity_data.get('columns', {})
                field_names = list(columns.keys())
                
                # Return a subset of important fields
                important_fields = []
                for field in field_names:
                    if field in ['id', 'payment_id', 'bill_id', 'customer_id', 'account_id', 
                                'amount', 'status', 'created_at', 'updated_at', 'bill_date']:
                        important_fields.append(field)
                
                return ' '.join(important_fields)
        
        # Fallback to common fields
        return 'id amount status created_at'
    
    def _build_simple_query(self, intent_info: Dict[str, Any]) -> str:
        """Build a simple GraphQL query when contract parsing fails"""
        filters = intent_info.get('filters', {})
        entities = intent_info.get('entities', ['payments'])
        
        # For multi-entity queries, build multiple queries
        if len(entities) > 1:
            return self._build_multi_entity_query(intent_info)
        
        # Build variables
        variables = {}
        filter_args = []
        
        # Add account filter if present
        if 'account_id' in filters:
            variables['account_id'] = filters['account_id']
            filter_args.append('account_id: $account_id')
        
        # Add country filter if present
        if 'country' in filters:
            variables['country'] = filters['country']
            filter_args.append('country: $country')
        
        # Add status filter if present
        if 'status' in filters:
            variables['status'] = filters['status']
            filter_args.append('status: $status')
        
        # Add bill status filter if present
        if 'bill_status' in filters:
            variables['bill_status'] = filters['bill_status']
            filter_args.append('status: $bill_status')
        
        # Add time range only for time-based entities
        if any(entity in entities for entity in ['payments', 'bills']):
            from datetime import datetime, timedelta
            now = datetime.now()
            from_time = now - timedelta(days=90)  # Default to 90 days
            
            variables['from_time'] = from_time.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
            variables['to_time'] = now.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
            filter_args.append('from_time: $from_time')
            filter_args.append('to_time: $to_time')
        
        # Determine the operation based on entities
        if 'payments' in entities:
            operation = 'list_payments'
            fields = 'payment_id account_id bill_id amount currency method status created_at updated_at'
        elif 'bills' in entities:
            operation = 'list_bills'
            fields = 'bill_id account_id amount_due status bill_date'
        elif 'customer_profile' in entities:
            operation = 'list_customer_profile'
            fields = 'customer_id full_name primary_email phone country segment status created_at updated_at'
        else:
            operation = 'list_payments'
            fields = 'payment_id account_id amount status created_at'
        
        # Build query with proper syntax
        if filter_args:
            filters_str = f"filters: {{ {', '.join(filter_args)} }}"
            query = f"""
            query {operation}($account_id: String, $country: String, $status: String, $bill_status: String, $from_time: String, $to_time: String) {{
                {operation}({filters_str}, limit: 50) {{
                    {fields}
                }}
            }}
            """
        else:
            query = f"""
            query {operation} {{
                {operation}(limit: 50) {{
                    {fields}
                }}
            }}
            """
        
        return json.dumps({
            'query': query.strip(),
            'variables': variables
        })
    
    def _build_multi_entity_query(self, intent_info: Dict[str, Any]) -> str:
        """Build multiple GraphQL queries for multi-entity requests"""
        filters = intent_info.get('filters', {})
        entities = intent_info.get('entities', ['payments'])
        
        queries = []
        all_variables = {}
        
        # Build variables
        from datetime import datetime, timedelta
        now = datetime.now()
        from_time = now - timedelta(days=90)
        
        # Use correct time filter names for different entities
        all_variables['from_time'] = from_time.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
        all_variables['to_time'] = now.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
        all_variables['from_date'] = from_time.strftime('%Y-%m-%d')
        all_variables['to_date'] = now.strftime('%Y-%m-%d')
        
        if 'account_id' in filters:
            all_variables['account_id'] = filters['account_id']
        if 'country' in filters:
            all_variables['country'] = filters['country']
        if 'status' in filters:
            all_variables['status'] = filters['status']
        if 'bill_status' in filters:
            all_variables['bill_status'] = filters['bill_status']
        
        # Build query for each entity
        for entity in entities:
            filter_args = []
            
            # Add relevant filters for each entity
            if 'account_id' in filters:
                filter_args.append('account_id: $account_id')
            if 'country' in filters and entity == 'customer_profile':
                filter_args.append('country: $country')
            if 'status' in filters and entity == 'payments':
                filter_args.append('status: $status')
            if 'bill_status' in filters and entity == 'bills':
                filter_args.append('status: $bill_status')
            
            # Add time filters with correct field names for each entity
            if entity == 'payments':
                filter_args.append('from_time: $from_time')
                filter_args.append('to_time: $to_time')
            elif entity == 'bills':
                filter_args.append('from_date: $from_date')
                filter_args.append('to_date: $to_date')
            
            # Determine operation and fields
            if entity == 'payments':
                operation = 'list_payments'
                fields = 'payment_id account_id bill_id amount currency method status created_at updated_at'
            elif entity == 'bills':
                operation = 'list_bills'
                fields = 'bill_id account_id amount_due status bill_date'
            elif entity == 'customer_profile':
                operation = 'list_customer_profile'
                fields = 'customer_id full_name primary_email phone country segment status created_at updated_at'
            else:
                continue
            
            # Build query with proper syntax
            if filter_args:
                filters_str = f"filters: {{ {', '.join(filter_args)} }}"
                query = f"""
            {operation}({filters_str}, limit: 50) {{
                {fields}
            }}
            """
            else:
                query = f"""
            {operation}(limit: 50) {{
                {fields}
            }}
            """
            queries.append(query)
        
        # Build variable declarations dynamically based on what's actually used
        # Extract variable names from the query string to avoid unused variables
        import re
        query_text = ''.join(queries)
        used_vars = set(re.findall(r'\$(\w+)', query_text))
        
        # Only declare variables that are actually used in the query
        used_variables = [f'${var}: String' for var in used_vars if var in all_variables]
        
        # Combine all queries
        if used_variables:
            variables_str = ', '.join(used_variables)
            combined_query = f"""
        query MultiEntityQuery({variables_str}) {{
            {''.join(queries)}
        }}
        """
        else:
            combined_query = f"""
        query MultiEntityQuery {{
            {''.join(queries)}
        }}
        """
        
        return json.dumps({
            'query': combined_query.strip(),
            'variables': all_variables,
            'multi_entity': True,
            'entities': entities,
            'intent': intent_info
        })
