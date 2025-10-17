"""
Query Builder Tools for CrewAI
Builds GraphQL queries from contracts and user intent
"""

import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool

# Set up debug logging
logger = logging.getLogger(__name__)


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
        # Log the tool invocation
        print(f"🔧 TOOL INVOKED: graphql_query_builder")
        print(f"🎯 Intent: {intent}")
        
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
            
            # Normalize contract data to a standard format
            contract = self._normalize_contract_data(contract_data)
            
            # Parse intent to extract key information
            intent_info = self._parse_intent(intent)
            
            # Check if this is a multi-entity query
            entities = intent_info.get('entities', [])
            if len(entities) > 1:
                # Multi-entity queries should use the simple query builder
                return self._build_simple_query(intent_info, contract)
            
            # Find matching operations from contract
            operations = self._find_matching_operations(intent_info, contract)
            
            if not operations:
                # Fallback: build a simple query directly
                return self._build_simple_query(intent_info, contract)
            
            # Build GraphQL query
            query_result = self._build_query(intent_info, operations[0], contract)
            
            return json.dumps(query_result)
            
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def _parse_intent(self, intent: str) -> Dict[str, Any]:
        """Parse user intent to extract key information"""
        intent_lower = intent.lower()
        
        # Extract entities using generic patterns
        entities = self._extract_entities_from_intent(intent_lower)
        
        # Extract actions using generic patterns
        actions = self._extract_actions_from_intent(intent_lower)
        
        # Extract filters using generic patterns
        filters = self._extract_filters_from_intent(intent_lower)
        
        # Check for multi-entity queries using generic patterns
        if self._is_multi_entity_query(intent_lower):
            entities = self._infer_multi_entities(intent_lower, entities)
        
        # Time filters - generic pattern for any time range
        time_patterns = [
            (r'last\s+(\d+)\s*days?', 'days'),
            (r'last\s+(\d+)\s*weeks?', 'weeks'),
            (r'last\s+(\d+)\s*months?', 'months'),
            (r'past\s+(\d+)\s*days?', 'days'),
            (r'recent\s+(\d+)\s*days?', 'days')
        ]
        
        for pattern, unit in time_patterns:
            match = re.search(pattern, intent_lower)
            if match:
                value = int(match.group(1))
                if unit == 'days':
                    from_time = datetime.now() - timedelta(days=value)
                elif unit == 'weeks':
                    from_time = datetime.now() - timedelta(weeks=value)
                elif unit == 'months':
                    from_time = datetime.now() - timedelta(days=value * 30)
                
                filters['from_time'] = from_time.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
                break
        
        return {
            'entities': entities,
            'actions': actions,
            'filters': filters,
            'original_intent': intent
        }
    
    def _extract_entities_from_intent(self, intent_lower: str) -> List[str]:
        """Extract entities from intent using generic patterns"""
        # Define entity patterns with their synonyms (simplified)
        entity_patterns = {
            'payments': ['payment', 'payments', 'transaction', 'transactions', 'money', 'financial', 'payment history'],
            'bills': ['bill', 'bills', 'invoice', 'invoices', 'statement', 'statements', 'billing', 'unpaid bills', 'unpaid bill'],
            'customer_profile': ['customer', 'customers', 'client', 'all customers'],
            'customer_subscriptions': ['subscription', 'subscriptions', 'plan', 'plans', 'service', 'services'],
            'customer_accounts': ['account', 'accounts', 'acc']
        }
        
        entities = []
        for entity_name, patterns in entity_patterns.items():
            if any(pattern in intent_lower for pattern in patterns):
                entities.append(entity_name)
        
        # If no entities found, default to payments
        return entities if entities else ['payments']
    
    def _extract_actions_from_intent(self, intent_lower: str) -> List[str]:
        """Extract actions from intent using generic patterns"""
        # Define action patterns with their synonyms
        action_patterns = {
            'list': ['show', 'list', 'display', 'find', 'search', 'get all', 'retrieve all'],
            'get': ['get', 'fetch', 'retrieve', 'lookup', 'find specific', 'get specific']
        }
        
        actions = []
        for action_name, patterns in action_patterns.items():
            if any(pattern in intent_lower for pattern in patterns):
                actions.append(action_name)
        
        # If no actions found, default to list
        return actions if actions else ['list']
    
    def _extract_filters_from_intent(self, intent_lower: str) -> Dict[str, Any]:
        """Extract filters from intent using completely generic patterns"""
        filters = {}
        
        # Extract all possible filters using generic patterns
        filters.update(self._extract_id_filters(intent_lower))
        filters.update(self._extract_status_filters(intent_lower))
        filters.update(self._extract_location_filters(intent_lower))
        filters.update(self._extract_time_filters(intent_lower))
        filters.update(self._extract_numeric_filters(intent_lower))
        
        return filters
    
    def _extract_id_filters(self, intent_lower: str) -> Dict[str, Any]:
        """Extract ID filters using generic patterns"""
        filters = {}
        
        # Generic ID patterns that work for any domain
        id_patterns = [
            # Pattern: "for account X" or "account X"
            (r'(?:for\s+)?(\w+)\s+([A-Z]+-\d+)', 'generic_id'),
            # Pattern: "X-123" format
            (r'([A-Z]+)-(\d+)', 'prefixed_id'),
            # Pattern: "ID 123" or "id 123"
            (r'(?:id|ID)\s+(\d+)', 'numeric_id'),
            # Pattern: "number 123" or "no 123"
            (r'(?:number|no|#)\s+(\d+)', 'numeric_id'),
            # Pattern: "code ABC123"
            (r'code\s+([A-Z0-9]+)', 'code_id')
        ]
        
        for pattern, id_type in id_patterns:
            match = re.search(pattern, intent_lower)
            if match:
                if id_type == 'generic_id':
                    entity_name = match.group(1).lower()
                    id_value = match.group(2)
                    filter_name = f'{entity_name}_id'
                    filters[filter_name] = id_value
                elif id_type == 'prefixed_id':
                    prefix = match.group(1).lower()
                    number = match.group(2)
                    filter_name = f'{prefix}_id'
                    filters[filter_name] = f'{prefix.upper()}-{number}'
                elif id_type == 'numeric_id':
                    number = match.group(1)
                    # Try to infer the entity type from context
                    entity_type = self._infer_entity_type_from_context(intent_lower)
                    filter_name = f'{entity_type}_id'
                    filters[filter_name] = number
                elif id_type == 'code_id':
                    code = match.group(1)
                    entity_type = self._infer_entity_type_from_context(intent_lower)
                    filter_name = f'{entity_type}_code'
                    filters[filter_name] = code
                break
        
        return filters
    
    def _extract_status_filters(self, intent_lower: str) -> Dict[str, Any]:
        """Extract status filters using generic patterns"""
        filters = {}
        
        # Generic status patterns
        status_patterns = [
            'active', 'enabled', 'live', 'running', 'online',
            'inactive', 'disabled', 'offline', 'dormant', 'closed',
            'pending', 'processing', 'waiting', 'queued',
            'completed', 'finished', 'done', 'successful',
            'failed', 'error', 'declined', 'rejected', 'cancelled',
            'paid', 'settled', 'cleared', 'unpaid', 'outstanding', 'due',
            'suspended', 'blocked', 'stopped', 'paused'
        ]
        
        for status_word in status_patterns:
            if status_word in intent_lower:
                # Use generic value mapping
                mapped_status = self._map_value(status_word, 'status')
                
                # Determine which status field to use based on context
                status_field = self._infer_status_field_from_context(intent_lower)
                filters[status_field] = mapped_status
                break
        
        return filters
    
    def _extract_location_filters(self, intent_lower: str) -> Dict[str, Any]:
        """Extract location filters using generic patterns"""
        filters = {}
        
        # Generic location patterns
        location_patterns = [
            (r'\bin\s+([a-zA-Z\s]+)', 'location'),
            (r'from\s+([a-zA-Z\s]+)', 'location'),
            (r'located\s+in\s+([a-zA-Z\s]+)', 'location'),
            (r'based\s+in\s+([a-zA-Z\s]+)', 'location'),
            (r'country\s+([a-zA-Z\s]+)', 'country'),
            (r'region\s+([a-zA-Z\s]+)', 'region'),
            (r'state\s+([a-zA-Z\s]+)', 'state'),
            (r'city\s+([a-zA-Z\s]+)', 'city')
        ]
        
        for pattern, location_type in location_patterns:
            match = re.search(pattern, intent_lower)
            if match:
                location = match.group(1).strip().title()
                # Use generic value mapping
                mapped_value = self._map_value(location, 'location')
                filters[location_type] = mapped_value
                break
        
        return filters
    
    def _extract_time_filters(self, intent_lower: str) -> Dict[str, Any]:
        """Extract time filters using generic patterns"""
        filters = {}
        
        # Generic time patterns
        time_patterns = [
            (r'last\s+(\d+)\s*days?', 'days'),
            (r'last\s+(\d+)\s*weeks?', 'weeks'),
            (r'last\s+(\d+)\s*months?', 'months'),
            (r'last\s+(\d+)\s*years?', 'years'),
            (r'past\s+(\d+)\s*days?', 'days'),
            (r'recent\s+(\d+)\s*days?', 'days'),
            (r'(\d+)\s*days?\s+ago', 'days'),
            (r'(\d+)\s*weeks?\s+ago', 'weeks'),
            (r'(\d+)\s*months?\s+ago', 'months')
        ]
        
        for pattern, unit in time_patterns:
            match = re.search(pattern, intent_lower)
            if match:
                value = int(match.group(1))
                from_time = self._calculate_time_from_now(value, unit)
                filters['from_time'] = from_time.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
                break
        
        return filters
    
    def _extract_numeric_filters(self, intent_lower: str) -> Dict[str, Any]:
        """Extract numeric filters using generic patterns"""
        filters = {}
        
        # Generic numeric patterns
        numeric_patterns = [
            (r'amount\s+([\d,]+\.?\d*)', 'amount'),
            (r'price\s+([\d,]+\.?\d*)', 'price'),
            (r'cost\s+([\d,]+\.?\d*)', 'cost'),
            (r'value\s+([\d,]+\.?\d*)', 'value'),
            (r'quantity\s+(\d+)', 'quantity'),
            (r'count\s+(\d+)', 'count'),
            (r'limit\s+(\d+)', 'limit'),
            (r'maximum\s+(\d+)', 'max_limit'),
            (r'minimum\s+(\d+)', 'min_limit')
        ]
        
        for pattern, filter_name in numeric_patterns:
            match = re.search(pattern, intent_lower)
            if match:
                value = match.group(1).replace(',', '')
                try:
                    # Try to convert to float for amounts, int for counts
                    if filter_name in ['amount', 'price', 'cost', 'value']:
                        filters[filter_name] = float(value)
                    else:
                        filters[filter_name] = int(value)
                except ValueError:
                    filters[filter_name] = value
                break
        
        return filters
    
    def _infer_entity_type_from_context(self, intent_lower: str) -> str:
        """Infer entity type from context"""
        if any(word in intent_lower for word in ['customer', 'client', 'user', 'person']):
            return 'customer'
        elif any(word in intent_lower for word in ['account', 'acc']):
            return 'account'
        elif any(word in intent_lower for word in ['payment', 'transaction']):
            return 'payment'
        elif any(word in intent_lower for word in ['bill', 'invoice']):
            return 'bill'
        elif any(word in intent_lower for word in ['order', 'purchase']):
            return 'order'
        elif any(word in intent_lower for word in ['product', 'item']):
            return 'product'
        else:
            return 'entity'  # Generic fallback
    
    def _infer_status_field_from_context(self, intent_lower: str) -> str:
        """Infer which status field to use based on context"""
        if any(word in intent_lower for word in ['bill', 'invoice', 'statement']):
            return 'bill_status'
        elif any(word in intent_lower for word in ['payment', 'transaction']):
            return 'payment_status'
        elif any(word in intent_lower for word in ['order', 'purchase']):
            return 'order_status'
        elif any(word in intent_lower for word in ['subscription', 'service']):
            return 'subscription_status'
        else:
            return 'status'  # Generic fallback
    
    def _calculate_time_from_now(self, value: int, unit: str) -> datetime:
        """Calculate time from now based on value and unit"""
        now = datetime.now()
        
        if unit == 'days':
            return now - timedelta(days=value)
        elif unit == 'weeks':
            return now - timedelta(weeks=value)
        elif unit == 'months':
            return now - timedelta(days=value * 30)
        elif unit == 'years':
            return now - timedelta(days=value * 365)
        else:
            return now - timedelta(days=value)
    
    def _map_value(self, value: str, value_type: str) -> str:
        """Generic value mapping helper for different value types"""
        value_lower = value.lower()
        
        if value_type == 'location':
            location_mapping = {
                'india': 'IN',
                'united states': 'US',
                'usa': 'US',
                'america': 'US',
                'united arab emirates': 'AE',
                'uae': 'AE',
                'dubai': 'AE',
                'new york': 'US',
                'california': 'US',
                'canada': 'CA',
                'united kingdom': 'GB',
                'uk': 'GB',
                'germany': 'DE',
                'france': 'FR',
                'australia': 'AU'
            }
            return location_mapping.get(value_lower, value)
        
        elif value_type == 'status':
            status_mapping = {
                'active': 'ACTIVE',
                'enabled': 'ACTIVE',
                'live': 'ACTIVE',
                'running': 'ACTIVE',
                'inactive': 'INACTIVE',
                'disabled': 'INACTIVE',
                'dormant': 'INACTIVE',
                'closed': 'INACTIVE',
                'suspended': 'SUSPENDED',
                'blocked': 'SUSPENDED',
                'stopped': 'SUSPENDED',
                'pending': 'PENDING',
                'processing': 'PENDING',
                'waiting': 'PENDING',
                'completed': 'COMPLETED',
                'finished': 'COMPLETED',
                'done': 'COMPLETED',
                'failed': 'FAILED',
                'error': 'FAILED',
                'declined': 'FAILED',
                'rejected': 'FAILED'
            }
            return status_mapping.get(value_lower, value.upper())
        
        elif value_type == 'currency':
            currency_mapping = {
                'dollar': 'USD',
                'dollars': 'USD',
                'usd': 'USD',
                'euro': 'EUR',
                'euros': 'EUR',
                'eur': 'EUR',
                'pound': 'GBP',
                'pounds': 'GBP',
                'gbp': 'GBP',
                'rupee': 'INR',
                'rupees': 'INR',
                'inr': 'INR',
                'dirham': 'AED',
                'dirhams': 'AED',
                'aed': 'AED'
            }
            return currency_mapping.get(value_lower, value.upper())
        
        # Default: return original value
        return value
    
    def _is_multi_entity_query(self, intent_lower: str) -> bool:
        """Check if the intent represents a multi-entity query"""
        multi_entity_indicators = [
            'and', 'with', 'including', 'also', 'additionally',
            'along with', 'together with', 'plus', 'as well as'
        ]
        
        return any(indicator in intent_lower for indicator in multi_entity_indicators)
    
    def _infer_multi_entities(self, intent_lower: str, current_entities: List[str]) -> List[str]:
        """Infer multiple entities based on context and relationships"""
        # Define common multi-entity patterns
        multi_entity_patterns = {
            'customer_bill_payment': ['customer', 'bill', 'payment'],
            'customer_payment': ['customer', 'payment'],
            'bill_payment': ['bill', 'payment'],
            'customer_subscription': ['customer', 'subscription'],
            'account_subscription': ['account', 'subscription']
        }
        
        # Check for specific multi-entity patterns
        for pattern_name, required_entities in multi_entity_patterns.items():
            if all(entity in intent_lower for entity in required_entities):
                # Map to actual entity names
                entity_mapping = {
                    'customer': 'customer_profile',
                    'bill': 'bills',
                    'payment': 'payments',
                    'subscription': 'customer_subscriptions',
                    'account': 'customer_accounts'
                }
                return [entity_mapping.get(entity, entity) for entity in required_entities]
        
        # If no specific pattern matches, return current entities
        return current_entities
    
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
    
    def _build_simple_query(self, intent_info: Dict[str, Any], contract: Dict[str, Any] = None) -> str:
        """Build a simple GraphQL query when contract parsing fails"""
        filters = intent_info.get('filters', {})
        entities = intent_info.get('entities', ['payments'])
        
        # For multi-entity queries, build multiple queries
        if len(entities) > 1:
            return self._build_multi_entity_query(intent_info, contract)
        
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
        
        result = {
            'query': query.strip(),
            'variables': variables
        }
        
        return json.dumps(result)
    
    def _build_multi_entity_query(self, intent_info: Dict[str, Any], contract: Dict[str, Any] = None) -> str:
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
        
        # Build query for each entity using generic metadata
        for entity in entities:
            # Get entity metadata from contract (if available)
            entity_metadata = self._get_entity_metadata(entity, contract)
            
            # Build filters for this entity using metadata
            filter_args = self._build_entity_filters(entity, filters, entity_metadata)
            
            # Get operation and fields using metadata
            operation = f'list_{entity}'
            fields = self._get_entity_fields(entity, entity_metadata)
            
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
        
        # Combine all queries with proper formatting
        if used_variables:
            variables_str = ', '.join(used_variables)
            combined_query = f"query MultiEntityQuery({variables_str}) {{ {''.join(queries)} }}"
        else:
            combined_query = f"query MultiEntityQuery {{ {''.join(queries)} }}"
        
        return json.dumps({
            'query': combined_query,
            'variables': all_variables,
            'multi_entity': True,
            'entities': entities,
            'intent': intent_info
        })
    
    def _normalize_contract_data(self, contract_data: str) -> Dict[str, Any]:
        """
        Normalize various contract data formats to a standard structure.
        Handles multiple input formats and provides sensible defaults.
        """
        if not contract_data or contract_data.strip() in ['{}', 'null', 'None']:
            return self._get_default_contract()
        
        # Try to parse as JSON first
        try:
            parsed = json.loads(contract_data)
            return self._standardize_contract_structure(parsed)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract information from string
            return self._extract_contract_from_string(contract_data)
    
    def _get_default_contract(self) -> Dict[str, Any]:
        """Get a default contract structure by reading from actual contract data or using minimal fallback"""
        # Try to get contract from the actual data source
        try:
            # This would ideally read from the actual contract/schema
            # For now, return a minimal generic structure
            return self._create_minimal_generic_contract()
        except Exception:
            # Ultimate fallback - completely generic structure
            return self._create_minimal_generic_contract()
    
    def _create_minimal_generic_contract(self) -> Dict[str, Any]:
        """Create a minimal generic contract that can work with any domain"""
        return {
            "entities": {
                "data": {
                    "aliases": ["list_data", "get_data"],
                    "columns": {
                        "id": "String",
                        "name": "String",
                        "status": "String",
                        "created_at": "Timestamp"
                    }
                }
            }
        }
    
    def _standardize_contract_structure(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize various contract structures to a common format"""
        # Handle different top-level structures
        if "data_product" in parsed_data:
            # Registry format: data_product -> entities
            return self._convert_registry_format(parsed_data)
        elif "product" in parsed_data and "entities" not in parsed_data:
            # Simple product format: {"product": "payments"}
            return self._convert_simple_product_format(parsed_data)
        elif "entities" in parsed_data:
            # Already in standard format, just ensure it's complete
            return self._ensure_contract_completeness(parsed_data)
        else:
            # Unknown format, try to extract entities
            return self._extract_entities_from_unknown_format(parsed_data)
    
    def _convert_registry_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert registry format to standard contract format"""
        entities = data.get("entities", {})
        standardized = {"entities": {}}
        
        for entity_name, entity_data in entities.items():
            if isinstance(entity_data, dict):
                # Extract all available information from registry format
                standardized["entities"][entity_name] = {
                    "aliases": entity_data.get("aliases", [f"list_{entity_name}", f"get_{entity_name}"]),
                    "columns": entity_data.get("columns", {}),
                    "filters": entity_data.get("filters", []),
                    "key": entity_data.get("key", f"{entity_name}_id"),
                    "table": entity_data.get("table", ""),
                    "order_by_default": entity_data.get("order_by_default", f"-created_at"),
                    "pagination": entity_data.get("pagination", {"default_limit": 50, "max_limit": 500})
                }
        
        return self._ensure_contract_completeness(standardized)
    
    def _convert_simple_product_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert simple product format to standard contract format"""
        product_name = data.get("product", "payments")
        
        # Get default columns for the product type
        default_columns = self._get_default_columns_for_product(product_name)
        
        return {
            "entities": {
                product_name: {
                    "aliases": [f"list_{product_name}", f"get_{product_name}"],
                    "columns": default_columns
                }
            }
        }
    
    def _get_default_columns_for_product(self, product_name: str) -> Dict[str, str]:
        """Get default column definitions by inferring from product name and common patterns"""
        # Try to infer column types from product name patterns
        inferred_columns = self._infer_columns_from_product_name(product_name)
        
        # Add common fields that most entities have
        common_fields = {
            "id": "String",
            "status": "String", 
            "created_at": "Timestamp"
        }
        
        # Merge inferred columns with common fields
        result = {**common_fields, **inferred_columns}
        
        return result
    
    def _infer_columns_from_product_name(self, product_name: str) -> Dict[str, str]:
        """Infer column types from product name using generic patterns"""
        product_lower = product_name.lower()
        columns = {}
        
        # ID field patterns
        if any(pattern in product_lower for pattern in ['payment', 'transaction']):
            columns[f"{product_name}_id"] = "String"
            columns["amount"] = "Decimal"
            columns["currency"] = "String"
        elif any(pattern in product_lower for pattern in ['bill', 'invoice']):
            columns[f"{product_name}_id"] = "String"
            columns["amount_due"] = "Decimal"
            columns["due_date"] = "Date"
        elif any(pattern in product_lower for pattern in ['customer', 'user', 'person']):
            columns[f"{product_name}_id"] = "String"
            columns["name"] = "String"
            columns["email"] = "String"
            columns["country"] = "String"
        elif any(pattern in product_lower for pattern in ['account']):
            columns[f"{product_name}_id"] = "String"
            columns["plan_code"] = "String"
            columns["billing_cycle"] = "Int"
        elif any(pattern in product_lower for pattern in ['subscription', 'service']):
            columns[f"{product_name}_id"] = "String"
            columns["product_id"] = "String"
            columns["start_date"] = "Date"
            columns["end_date"] = "Date"
        else:
            # Generic fallback
            columns[f"{product_name}_id"] = "String"
            columns["name"] = "String"
            columns["description"] = "String"
        
        return columns
    
    def _ensure_contract_completeness(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure contract has all required fields with sensible defaults"""
        entities = contract.get("entities", {})
        
        for entity_name, entity_data in entities.items():
            if not isinstance(entity_data, dict):
                continue
                
            # Ensure aliases exist
            if "aliases" not in entity_data:
                entity_data["aliases"] = [f"list_{entity_name}", f"get_{entity_name}"]
            
            # Ensure columns exist
            if "columns" not in entity_data or not entity_data["columns"]:
                entity_data["columns"] = self._get_default_columns_for_product(entity_name)
        
        return contract
    
    def _extract_entities_from_unknown_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Try to extract entity information from unknown data formats"""
        entities = {}
        
        # Look for common patterns
        for key, value in data.items():
            if isinstance(value, dict) and any(col in str(value) for col in ["id", "name", "status"]):
                entities[key] = {
                    "aliases": [f"list_{key}", f"get_{key}"],
                    "columns": self._infer_columns_from_data(value)
                }
        
        if not entities:
            # Fallback to default
            return self._get_default_contract()
        
        return {"entities": entities}
    
    def _infer_columns_from_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Infer column types from sample data"""
        columns = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                if any(date_indicator in key.lower() for date_indicator in ["date", "time", "created", "updated"]):
                    columns[key] = "Timestamp"
                elif any(id_indicator in key.lower() for id_indicator in ["id", "key"]):
                    columns[key] = "String"
                else:
                    columns[key] = "String"
            elif isinstance(value, (int, float)):
                columns[key] = "Decimal"
            elif isinstance(value, bool):
                columns[key] = "Boolean"
            else:
                columns[key] = "String"
        
        return columns
    
    def _extract_contract_from_string(self, contract_data: str) -> Dict[str, Any]:
        """Extract contract information from non-JSON string data"""
        # Look for common patterns in the string
        if "payments" in contract_data.lower():
            return self._get_default_contract()
        elif "bills" in contract_data.lower():
            return {
                "entities": {
                    "bills": {
                        "aliases": ["list_bills", "get_bill"],
                        "columns": self._get_default_columns_for_product("bills")
                    }
                }
            }
        elif "customer" in contract_data.lower():
            return {
                "entities": {
                    "customer_profile": {
                        "aliases": ["list_customer_profile", "get_customer"],
                        "columns": self._get_default_columns_for_product("customer_profile")
                    }
                }
            }
        else:
            # Default fallback
            return self._get_default_contract()
    
    def _get_entity_metadata(self, entity_name: str, contract: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get metadata for an entity from contract or infer from name"""
        if contract and 'entities' in contract:
            # Try to read from actual contract data
            entity_data = contract['entities'].get(entity_name)
            if entity_data and 'columns' in entity_data:
                return self._extract_metadata_from_contract(entity_data)
        
        # Fallback: infer from entity name patterns
        return {
            'time_fields': self._infer_time_fields(entity_name),
            'id_fields': self._infer_id_fields(entity_name),
            'status_fields': self._infer_status_fields(entity_name)
        }
    
    def _extract_metadata_from_contract(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from actual contract entity data"""
        columns = entity_data.get('columns', {})
        
        # Extract time fields from column names
        time_fields = {}
        for col_name, col_type in columns.items():
            col_lower = col_name.lower()
            if 'created' in col_lower or 'updated' in col_lower:
                time_fields['created'] = col_name
            elif 'date' in col_lower and 'time' not in col_lower:
                time_fields['from'] = f'from_{col_name}'
                time_fields['to'] = f'to_{col_name}'
            elif 'time' in col_lower:
                time_fields['from'] = f'from_{col_name}'
                time_fields['to'] = f'to_{col_name}'
        
        # Extract ID fields from column names
        id_fields = []
        for col_name in columns.keys():
            col_lower = col_name.lower()
            if col_lower.endswith('_id') or col_lower == 'id':
                id_fields.append(col_name)
        
        # Extract status fields from column names
        status_fields = []
        for col_name in columns.keys():
            col_lower = col_name.lower()
            if 'status' in col_lower:
                status_fields.append(col_name)
        
        return {
            'time_fields': time_fields,
            'id_fields': id_fields,
            'status_fields': status_fields,
            'columns': columns
        }
    
    def _infer_time_fields(self, entity_name: str) -> Dict[str, str]:
        """Infer time field names from entity name"""
        entity_lower = entity_name.lower()
        
        if any(pattern in entity_lower for pattern in ['payment', 'transaction']):
            return {'created': 'created_at', 'from': 'from_time', 'to': 'to_time'}
        elif any(pattern in entity_lower for pattern in ['bill', 'invoice']):
            return {'created': 'bill_date', 'from': 'from_date', 'to': 'to_date'}
        else:
            return {'created': 'created_at', 'from': 'from_time', 'to': 'to_time'}
    
    def _infer_id_fields(self, entity_name: str) -> List[str]:
        """Infer ID field names from entity name"""
        entity_lower = entity_name.lower()
        
        if any(pattern in entity_lower for pattern in ['customer', 'user', 'person']):
            return ['customer_id', 'account_id']
        elif any(pattern in entity_lower for pattern in ['account']):
            return ['account_id']
        else:
            return [f'{entity_name}_id', 'id']
    
    def _infer_status_fields(self, entity_name: str) -> List[str]:
        """Infer status field names from entity name"""
        entity_lower = entity_name.lower()
        
        if any(pattern in entity_lower for pattern in ['bill', 'invoice']):
            return ['bill_status', 'status']
        else:
            return ['status']
    
    def _build_entity_filters(self, entity: str, filters: Dict[str, Any], entity_metadata: Dict[str, Any]) -> List[str]:
        """Build filter arguments for an entity using metadata with proper field mapping"""
        filter_args = []
        entity_lower = entity.lower()
        
        # Map generic filter names to entity-specific filter names
        filter_mapping = self._get_entity_filter_mapping(entity, entity_metadata)
        
        # Add ID filters
        for filter_name, filter_value in filters.items():
            if filter_name in filter_mapping:
                entity_filter_name = filter_mapping[filter_name]
                filter_args.append(f'{entity_filter_name}: ${filter_name}')
        
        # Add geographic filters (only for customer entities)
        if 'country' in filters and any(pattern in entity_lower for pattern in ['customer', 'user', 'person']):
            filter_args.append('country: $country')
        
        # Add time filters
        time_fields = entity_metadata.get('time_fields', {})
        if 'from_time' in filters and 'from' in time_fields:
            filter_args.append(f'{time_fields["from"]}: ${time_fields["from"]}')
        if 'to_time' in filters and 'to' in time_fields:
            filter_args.append(f'{time_fields["to"]}: ${time_fields["to"]}')
        
        return filter_args
    
    def _get_entity_filter_mapping(self, entity: str, entity_metadata: Dict[str, Any]) -> Dict[str, str]:
        """Get mapping from generic filter names to entity-specific filter names"""
        entity_lower = entity.lower()
        
        # Base mapping for common filters
        mapping = {}
        
        # Map status filters to entity-specific status fields
        if any(pattern in entity_lower for pattern in ['customer', 'user', 'person']):
            if 'status' in entity_metadata.get('status_fields', []):
                mapping['status'] = 'status'
        elif any(pattern in entity_lower for pattern in ['payment', 'transaction']):
            if 'status' in entity_metadata.get('status_fields', []):
                mapping['status'] = 'status'
        elif any(pattern in entity_lower for pattern in ['bill', 'invoice']):
            if 'status' in entity_metadata.get('status_fields', []):
                mapping['status'] = 'status'
                mapping['bill_status'] = 'status'  # Map bill_status to status for bills
        
        # Map ID filters to entity-specific ID fields
        id_fields = entity_metadata.get('id_fields', [])
        for id_field in id_fields:
            if 'customer' in id_field:
                mapping['customer_id'] = id_field
            elif 'account' in id_field:
                mapping['account_id'] = id_field
            elif 'payment' in id_field:
                mapping['payment_id'] = id_field
            elif 'bill' in id_field:
                mapping['bill_id'] = id_field
        
        return mapping
    
    def _get_entity_fields(self, entity: str, entity_metadata: Dict[str, Any]) -> str:
        """Get field list for an entity using metadata with smart prioritization"""
        # Use actual contract columns if available
        if 'columns' in entity_metadata:
            columns = entity_metadata['columns']
            return self._select_important_fields_from_contract(columns, entity)
        
        # Fallback: use generic fields based on entity type
        return self._get_fallback_fields_for_entity(entity)
    
    def _select_important_fields_from_contract(self, columns: Dict[str, Any], entity: str) -> str:
        """Select the most important fields from actual contract columns"""
        # Define field priority patterns for different entity types
        entity_lower = entity.lower()
        
        if any(pattern in entity_lower for pattern in ['customer', 'user', 'person']):
            priority_patterns = ['customer_id', 'full_name', 'primary_email', 'country', 'status', 'created_at']
        elif any(pattern in entity_lower for pattern in ['payment', 'transaction']):
            priority_patterns = ['payment_id', 'amount', 'currency', 'status', 'created_at', 'account_id']
        elif any(pattern in entity_lower for pattern in ['bill', 'invoice']):
            priority_patterns = ['bill_id', 'amount_due', 'status', 'bill_date', 'account_id']
        elif any(pattern in entity_lower for pattern in ['account']):
            priority_patterns = ['account_id', 'customer_id', 'plan_code', 'status', 'created_at']
        elif any(pattern in entity_lower for pattern in ['subscription', 'service']):
            priority_patterns = ['subscription_id', 'account_id', 'product_id', 'status', 'start_date']
        else:
            # Generic priority patterns
            priority_patterns = ['id', 'name', 'status', 'created_at', 'amount', 'email']
        
        # Select fields based on priority patterns
        selected_fields = []
        
        # First, try exact matches with priority patterns
        for pattern in priority_patterns:
            if pattern in columns:
                selected_fields.append(pattern)
                if len(selected_fields) >= 6:
                    break
        
        # If we don't have enough fields, add other important fields
        if len(selected_fields) < 6:
            for col_name in columns.keys():
                if col_name not in selected_fields:
                    col_lower = col_name.lower()
                    if any(important in col_lower for important in ['id', 'name', 'status', 'amount', 'date', 'time', 'email', 'country']):
                        selected_fields.append(col_name)
                        if len(selected_fields) >= 6:
                            break
        
        return ' '.join(selected_fields) if selected_fields else self._get_fallback_fields_for_entity(entity)
    
    def _get_fallback_fields_for_entity(self, entity: str) -> str:
        """Get fallback field names when contract data is not available"""
        entity_lower = entity.lower()
        
        if any(pattern in entity_lower for pattern in ['payment', 'transaction']):
            return 'payment_id amount currency status created_at account_id'
        elif any(pattern in entity_lower for pattern in ['bill', 'invoice']):
            return 'bill_id amount_due status bill_date account_id'
        elif any(pattern in entity_lower for pattern in ['customer', 'user', 'person']):
            return 'customer_id full_name primary_email country status created_at'
        elif any(pattern in entity_lower for pattern in ['account']):
            return 'account_id customer_id plan_code status created_at'
        elif any(pattern in entity_lower for pattern in ['subscription', 'service']):
            return 'subscription_id account_id product_id status start_date'
        else:
            return 'id name status created_at'
