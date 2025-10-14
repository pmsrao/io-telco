"""
Query Builder Tools for CrewAI
Builds GraphQL queries from contracts and user intent
"""

import json
import re
from typing import Dict, Any, List, Optional
from crewai_tools import BaseTool


class GraphQLQueryBuilderTool(BaseTool):
    name: str = "graphql_query_builder"
    description: str = "Build GraphQL queries from user intent and contract information"
    
    def _run(self, intent: str, contract_data: str, schema_data: str = None) -> str:
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
            contract = json.loads(contract_data)
            
            # Parse intent to extract key information
            intent_info = self._parse_intent(intent)
            
            # Find matching operations from contract
            operations = self._find_matching_operations(intent_info, contract)
            
            if not operations:
                return json.dumps({"error": "No matching operations found for the given intent"})
            
            # Build GraphQL query
            query_result = self._build_query(intent_info, operations[0], contract)
            
            return json.dumps(query_result)
            
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def _parse_intent(self, intent: str) -> Dict[str, Any]:
        """Parse user intent to extract key information"""
        intent_lower = intent.lower()
        
        # Extract entity types
        entities = []
        if any(word in intent_lower for word in ['payment', 'payments']):
            entities.append('payments')
        if any(word in intent_lower for word in ['bill', 'bills']):
            entities.append('bills')
        if any(word in intent_lower for word in ['customer', 'customers']):
            entities.append('customer_profile')
        if any(word in intent_lower for word in ['account', 'accounts']):
            entities.append('customer_accounts')
        if any(word in intent_lower for word in ['subscription', 'subscriptions']):
            entities.append('customer_subscriptions')
        
        # Extract action types
        actions = []
        if any(word in intent_lower for word in ['show', 'list', 'get', 'find', 'search']):
            actions.append('list')
        if any(word in intent_lower for word in ['get', 'fetch', 'retrieve']):
            actions.append('get')
        
        # Extract filters
        filters = {}
        
        # Account ID
        account_match = re.search(r'acc[_-]?(\d+)', intent_lower)
        if account_match:
            filters['account_id'] = f"ACC-{account_match.group(1)}"
        
        # Bill ID
        bill_match = re.search(r'bill[_-]?(\d+)', intent_lower)
        if bill_match:
            filters['bill_id'] = f"BILL-{bill_match.group(1)}"
        
        # Status
        if 'posted' in intent_lower:
            filters['status'] = 'POSTED'
        elif 'failed' in intent_lower:
            filters['status'] = 'FAILED'
        elif 'open' in intent_lower:
            filters['status'] = 'OPEN'
        
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
            query {operation}(${', '.join(f'${var}: String!' for var in variables.keys())}) {{
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
