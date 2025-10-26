"""Digital lending processor for eligibility checks"""
import logging
import re
from typing import Dict, Any, List
from processors.base import BaseProcessor, Tool
from processors.digital_lending.data_manager import DataManager
from models.response import Response

logger = logging.getLogger(__name__)

class DigitalLendingProcessor(BaseProcessor):
    """Handles loan eligibility and ineligibility checks"""
    
    def __init__(self):
        super().__init__()
        self.name = "digital_lending"
        self.description = "Handles loan eligibility and ineligibility checks"
        self.validation_level = "light"
        
        # Initialize data manager
        self.data_manager = DataManager(
            warehouse_file="processors/digital_lending/data/warehouse.csv",
            reasons_file="processors/digital_lending/data/reasons.csv"
        )
        
        self.tools = [
            Tool(
                name="check_eligibility",
                description="Check if customer qualifies for digital loan. Requires account/customer number.",
                parameters_schema={
                    "account_number": {
                        "type": "string",
                        "required": True,
                        "description": "Customer account or customer number"
                    }
                },
                processor_class=self.__class__
            )
        ]
    
    def get_tools(self) -> List[Tool]:
        """Return available tools"""
        return self.tools
    
    def execute(self, tool_name: str, arguments: Dict[str, Any],
                context: Dict[str, Any], llm_provider: Any) -> Response:
        """Execute tool"""
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        if tool_name == "check_eligibility":
            return self._check_eligibility(arguments, context, llm_provider)
        else:
            return Response(
                message="Unknown tool requested",
                intent="error",
                confidence=0.0,
                status="error"
            )
    
    def _check_eligibility(self, arguments: Dict, context: Dict, 
                          llm_provider: Any) -> Response:
        """Check customer eligibility"""
        account_number = arguments.get("account_number")
        
        if not account_number:
            return Response(
                message="I need an account number to check eligibility. Please provide it.",
                intent="eligibility_check",
                confidence=0.8,
                status="missing_data",
                suggestions=["Check eligibility for account 503446"]
            )
        
        # Clean account number
        account_number = str(account_number).strip()
        
        logger.info(f"Checking eligibility for: {account_number}")
        
        # Step 1: Check warehouse (eligible customers)
        in_warehouse, actual_account = self.data_manager.is_in_warehouse(account_number)
        
        if in_warehouse:
            logger.info(f"Customer {account_number} is ELIGIBLE")
            return self._generate_eligible_response(actual_account, llm_provider)
        
        # Step 2: Check reasons file (ineligible customers)
        customer_data = self.data_manager.get_customer_data(account_number)
        
        if not customer_data:
            logger.info(f"Customer {account_number} not found")
            return Response(
                message=f"Account {account_number} not found in records. Please verify the account number.",
                intent="eligibility_check",
                confidence=0.9,
                status="not_found"
            )
        
        # Step 3: Analyze failed checks
        logger.info(f"Customer {account_number} is INELIGIBLE")
        return self._generate_ineligible_response(customer_data, llm_provider)
    
    def _generate_eligible_response(self, account_number: str, 
                                    llm_provider: Any) -> Response:
        """Generate response for eligible customer"""
        from datetime import datetime
        
        # Time-based greeting
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good Morning,"
        elif 12 <= hour < 17:
            greeting = "Good Afternoon,"
        else:
            greeting = "Good Evening,"
        
        message = f"""{greeting}

**Digital Loan Status: ELIGIBLE**

Customer with account {account_number} is eligible for a digital loan.

**Next Steps:**
• Inform customer they qualify for a loan
• Guide them through the loan application process
• Ensure they understand the terms and conditions
• Process loan request through standard channels

For specific loan limits, please check the warehouse system or contact Portfolio Management."""
        
        return Response(
            message=message,
            intent="eligibility_check",
            confidence=0.95,
            status="success",
            data={
                'is_eligible': True,
                'account_number': account_number
            }
        )
    
    def _generate_ineligible_response(self, customer_data: Dict, 
                                      llm_provider: Any) -> Response:
        """Generate response for ineligible customer"""
        from datetime import datetime
        
        # Time-based greeting
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good Morning,"
        elif 12 <= hour < 17:
            greeting = "Good Afternoon,"
        else:
            greeting = "Good Evening,"
        
        # Extract customer info
        customer_name = customer_data.get('CUS_NAME_1', 'Customer')
        account_number = customer_data.get('ACCOUNT_NUMBER', 'Unknown')
        
        # Analyze failed checks
        failed_checks = self._analyze_failed_checks(customer_data)
        
        # Build response
        message = f"""{greeting}

**Digital Loan Status: NOT ELIGIBLE**

{customer_name} (Account: {account_number}) is currently not eligible for a digital loan.

**Issues Identified:**
"""
        
        # Add each failed check
        for idx, check in enumerate(failed_checks, 1):
            message += f"\n{idx}. **{check['description']}**"
            message += f"\n   {check['explanation']}"
            if check.get('supporting_data'):
                for key, value in check['supporting_data'].items():
                    message += f"\n   • {key}: {value}"
        
        # Add resolution steps
        message += "\n\n**Resolution Required:**"
        actions = self._generate_action_items(failed_checks)
        for action in actions:
            message += f"\n{action}"
        
        return Response(
            message=message,
            intent="eligibility_check",
            confidence=0.95,
            status="success",
            data={
                'is_eligible': False,
                'account_number': account_number,
                'customer_name': customer_name,
                'failed_checks': failed_checks
            }
        )
    
    def _analyze_failed_checks(self, customer_data: Dict) -> List[Dict]:
        """Analyze which eligibility checks failed"""
        failed_checks = []
        
        # Check recency
        if str(customer_data.get('recency_check', '')).strip().upper() == 'N':
            failed_checks.append({
                'check_type': 'recency_check',
                'description': 'Inconsistent Credit Turnovers',
                'explanation': 'Customer has inconsistent credit turnovers with irregular transaction patterns',
                'supporting_data': {}
            })
        
        # Define check columns
        CHECK_COLUMNS = {
            'Joint_Check': 'Joint Account Check',
            'DPD_Arrears_Check_DS': 'DPD Arrears Check',
            'Elma_check': 'Mobile Banking Setup',
            'KRAPIN_Check': 'KRA PIN Check',
            'Classification_Check': 'Risk Classification',
            'Mandates_Check': 'Account Mandates',
            'Linked_Base_Check': 'Linked Base Account',
            'customer_vintage_Check': 'Banking Vintage',
            'Active_Inactive_Check': 'Account Activity',
            'Scheme_Check_DS': 'Scheme Check',
            'Staff_Check_DS': 'Staff Account Check',
            'Risk_Class_Check_DS': 'Risk Class Check',
            'Average_Bal_check': 'Average Balance Check'
        }
        
        # Check each column
        for col, description in CHECK_COLUMNS.items():
            value = str(customer_data.get(col, '')).strip().upper()
            
            if value == 'EXCLUDE':
                explanation = self._get_check_explanation(col, customer_data)
                supporting_data = self._get_supporting_data(col, customer_data)
                
                failed_checks.append({
                    'check_type': col,
                    'description': description,
                    'explanation': explanation,
                    'supporting_data': supporting_data
                })
        
        # Check reasons column
        reasons = str(customer_data.get('reasons', '')).strip()
        if reasons and reasons != 'nan':
            reason_list = [r.strip() for r in reasons.split(',')]
            reasons_explanation = str(customer_data.get('reasons_explanation', '')).strip()
            
            if reasons_explanation and reasons_explanation != 'nan':
                explanation_list = [e.strip() for e in reasons_explanation.split(',')]
            else:
                explanation_list = reason_list
            
            for idx, reason in enumerate(reason_list):
                if reason and reason not in [fc['check_type'] for fc in failed_checks]:
                    failed_checks.append({
                        'check_type': reason,
                        'description': reason.replace('_', ' ').title(),
                        'explanation': explanation_list[idx] if idx < len(explanation_list) else reason,
                        'supporting_data': {}
                    })
        
        return failed_checks
    
    def _get_check_explanation(self, check_type: str, customer_data: Dict) -> str:
        """Get human-readable explanation for failed check"""
        explanations = {
            'DPD_Arrears_Check_DS': lambda: (
                f"Customer has DPD arrears. Clear all outstanding arrears and wait 60-day cooling period."
            ),
            'Classification_Check': lambda: (
                f"Customer classification is {customer_data.get('RISK_CLASS', 'Unknown')}, "
                f"below minimum threshold (A5 for digital, A7 for mobile). Liaise with RM to upgrade."
            ),
            'Joint_Check': lambda: (
                "This is a joint account. Only individual accounts with sole signatories qualify."
            ),
            'Mandates_Check': lambda: (
                "Account mandates must be SOLE SIGNATORY. Remove additional signatories."
            ),
            'customer_vintage_Check': lambda: (
                "Customer has banked less than 6 months. Minimum 6 months required."
            ),
            'Elma_check': lambda: (
                "Customer not enrolled in mobile banking. Register for NCBA SASA mobile banking."
            ),
            'Active_Inactive_Check': lambda: (
                "Account classified as inactive. Reactivate through regular transactions for 30+ days."
            ),
            'Risk_Class_Check_DS': lambda: (
                "Customer classified as high risk after assessment. Improve credit history."
            )
        }
        
        explanation_func = explanations.get(check_type, lambda: f"Failed {check_type.replace('_', ' ')}")
        return explanation_func()
    
    def _get_supporting_data(self, check_type: str, customer_data: Dict) -> Dict:
        """Extract supporting data for failed check"""
        if check_type == 'DPD_Arrears_Check_DS':
            return {
                'Arrears_Days': customer_data.get('Arrears_Days', 'N/A'),
                'Loan_Account': customer_data.get('Loan_Account', 'N/A')
            }
        elif check_type == 'Classification_Check':
            return {
                'Current_Classification': customer_data.get('RISK_CLASS', 'Unknown')
            }
        
        return {}
    
    def _generate_action_items(self, failed_checks: List[Dict]) -> List[str]:
        """Generate actionable steps for resolution"""
        actions = []
        action_map = {}
        
        for check in failed_checks:
            check_type = check['check_type'].lower()
            
            if 'dpd' in check_type or 'arrears' in check_type:
                if 'arrears' not in action_map:
                    actions.append("• **Clear all arrears** and wait 60-day cooling period")
                    action_map['arrears'] = True
            
            elif 'classification' in check_type:
                if 'classification' not in action_map:
                    actions.append("• **Upgrade customer classification** - Contact RM/Portfolio team")
                    action_map['classification'] = True
            
            elif 'joint' in check_type:
                if 'joint' not in action_map:
                    actions.append("• **Convert to individual account** - Joint accounts ineligible")
                    action_map['joint'] = True
            
            elif 'mandates' in check_type:
                if 'mandates' not in action_map:
                    actions.append("• **Update to SOLE SIGNATORY** - Remove additional signatories")
                    action_map['mandates'] = True
            
            elif 'vintage' in check_type:
                if 'vintage' not in action_map:
                    actions.append("• **Wait minimum 6 months** banking relationship")
                    action_map['vintage'] = True
            
            elif 'elma' in check_type:
                if 'elma' not in action_map:
                    actions.append("• **Register for mobile banking** - Setup NCBA SASA")
                    action_map['elma'] = True
            
            elif 'active' in check_type or 'inactive' in check_type:
                if 'active' not in action_map:
                    actions.append("• **Reactivate account** - Regular transactions for 30+ days")
                    action_map['active'] = True
        
        if not actions:
            actions.append("• Contact Portfolio Management for detailed review")
        
        return actions

