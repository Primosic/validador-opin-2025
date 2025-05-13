import os
import logging
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session

from .schema_extractor import extract_schemas_from_yaml, get_api_name_from_yaml
from .repository import upsert_grupo, upsert_conjunto_dados, upsert_regra_validacao

# Configuracao de logging
logger = logging.getLogger(__name__)


def is_insurance_related_file(yaml_path: str) -> bool:
    """
    Verifica se um arquivo YAML estu00e1 relacionado a seguros para aplicar regras especu00edficas.
    
    Args:
        yaml_path: Caminho do arquivo YAML
        
    Returns:
        bool: True se o arquivo estiver relacionado a seguros, False caso contru00e1rio
    """
    basename = os.path.basename(yaml_path).lower()
    
    # Arquivos que comeu00e7am com 'insurance-' su00e3o relacionados a seguros
    if basename.startswith('insurance'):
        return True
    
    # Casos especu00edficos de arquivos relacionados a seguros com nomenclatura diferente
    special_files = ['person.yaml', 'resources_v2.yaml']
    if basename in special_files:
        return True
        
    return False


def process_yaml_to_db(yaml_path: str, api_name: str, session: Session) -> bool:
    """
    Processa um arquivo YAML para extrau00e7u00e3o de schemas e persistu00eancia no banco de dados.
    
    Args:
        yaml_path: Caminho para o arquivo YAML
        api_name: Nome da API associada ao arquivo YAML
        session: Sessu00e3o do SQLAlchemy para persistu00eancia
        
    Returns:
        bool: True se o processamento foi bem-sucedido, False caso contru00e1rio
    """
    try:
        # Extrai os schemas do YAML
        schemas = extract_schemas_from_yaml(yaml_path)
        if not schemas:
            logger.warning(f"Nenhum schema encontrado em {yaml_path}")
            return False
            
        # Define o nome do grupo (tag principal do YAML ou nome do arquivo)
        # Isso define como seru00e1 agrupado no banco de dados
        api_name_from_yaml = get_api_name_from_yaml(yaml_path)
        if api_name_from_yaml:
            logger.info(f"Nome da API extrau00eddo do YAML: {api_name_from_yaml}")
            grupo_nome = api_name_from_yaml
        else:
            grupo_nome = api_name
            
        logger.info(f"Usando o nome da tag '{grupo_nome}' como nome do grupo (arquivo: {os.path.basename(yaml_path).split('.')[0]})")
        
        # Cria/atualiza o grupo no banco de dados
        grupo_id = upsert_grupo(session, grupo_nome)
        logger.info(f"API '{grupo_nome}' persistida com ID {grupo_id}")
        
        # Processa cada schema para criar conjuntos de dados e regras de validau00e7u00e3o
        processed_schemas = []
        yaml_is_insurance = is_insurance_related_file(yaml_path)
        
        for schema_name, schema_data in schemas.items():
            # Verifica se deve ignorar este schema (caso seja referenciado apenas)
            if schema_name == "AmountDetails" and yaml_is_insurance:
                logger.info(f"Pulando criau00e7u00e3o do conjunto {schema_name}, pois seus campos su00e3o incorporados em outros conjuntos (via $ref ou allOf)")
                continue
                
            # Cria/atualiza o conjunto de dados no banco
            conjunto_id = upsert_conjunto_dados(session, schema_name, grupo_id)
            logger.info(f"Novo conjunto '{schema_name}' criado com ID {conjunto_id}")
            
            # Se for arquivo de seguro, adiciona o campo policyId como obrigatu00f3rio
            if yaml_is_insurance:
                logger.info(f"Adicionando propriedade policyId ao schema {schema_name}")
                
                # Adiciona o campo policyId se nu00e3o existir
                if "policyId" not in schema_data.get("properties", {}):
                    if "properties" not in schema_data:
                        schema_data["properties"] = {}
                    
                    schema_data["properties"]["policyId"] = {
                        "type": "string",
                        "maxLength": 100,
                        "description": "Identificador u00fanico da apu00f3lice"
                    }
                    
                    # Adiciona o campo como obrigatu00f3rio
                    if "required" not in schema_data:
                        schema_data["required"] = []
                        
                    if "policyId" not in schema_data["required"]:
                        schema_data["required"].append("policyId")
                        logger.info(f"Adicionando policyId como campo obrigatu00f3rio em {schema_name}")
            
            # Coleta os campos para criar regras de validau00e7u00e3o
            fields_processed = process_schema_fields(session, schema_name, schema_data, conjunto_id, yaml_is_insurance)
            
            if fields_processed > 0:
                processed_schemas.append(schema_name)
                logger.info(f"Schema '{schema_name}' processado com {fields_processed} campos")
        
        if processed_schemas:
            logger.info(f"Persistu00eancia concluu00edda para {grupo_nome}. Schemas processados: {len(processed_schemas)}")
            logger.info(f"Persistu00eancia concluu00edda com sucesso para {os.path.basename(yaml_path).split('.')[0]}")
            return True
        else:
            logger.warning(f"Nenhum schema processado com sucesso em {yaml_path}")
            return False
            
    except Exception as e:
        logger.error(f"Erro ao processar {yaml_path}: {str(e)}")
        return False


def process_schema_fields(session: Session, schema_name: str, schema_data: Dict[str, Any], 
                       conjunto_id: int, is_insurance_schema: bool) -> int:
    """
    Processa os campos de um schema e cria regras de validau00e7u00e3o.
    
    Args:
        session: Sessu00e3o do SQLAlchemy
        schema_name: Nome do schema
        schema_data: Dados do schema
        conjunto_id: ID do conjunto de dados
        is_insurance_schema: Se o schema estu00e1 em um arquivo relacionado a seguros
        
    Returns:
        int: Nu00famero de campos processados
    """
    processed_count = 0
    meta = schema_data.copy()
    
    # Extrai informau00e7u00f5es bu00e1sicas do schema
    required_fields = meta.get("required", [])
    properties = meta.get("properties", {})
    all_of = meta.get("allOf", [])
    
    # Processa combinau00e7u00f5es allOf (para incorporar AmountDetails, por exemplo)
    processed_properties = properties.copy()
    
    # Processa referu00eancias allOf (comum em schemas que referenciam AmountDetails)
    if all_of:
        for item in all_of:
            # Verifica se hu00e1 uma referu00eancia a outro schema
            if "$ref" in item and "/AmountDetails" in item["$ref"]:
                if "properties" in item:
                    ref_properties = item.get("properties", {})
                    
                    # Incorpora propriedades do schema referenciado
                    for prop_name, prop_data in ref_properties.items():
                        # Propriedades especiais como 'amount' em AmountDetails
                        if prop_name == "amount" and "properties" in prop_data:
                            logger.info(f"Incorporando campos de AmountDetails para amount em {schema_name} (incluindo subcampos aninhados)")
                            
                            # Processa todos os campos de amount
                            for sub_field, sub_data in prop_data.get("properties", {}).items():
                                field_name = f"amount_{sub_field}"
                                
                                # Processa tamanho do campo
                                field_size = calculate_field_size(sub_field, sub_data)
                                
                                # Processa tipo do campo
                                field_type = extract_field_type(sub_data)
                                
                                # Adiciona o campo u00e0 lista de propriedades processadas
                                processed_properties[field_name] = {
                                    "type": field_type,
                                    "maxLength": field_size
                                }
                                
                                # Processa o caso especial de 'unit' que tem subcampos aninhados
                                if sub_field == "unit" and "properties" in sub_data:
                                    logger.info(f"Processando campo especial 'unit' para amount com seus subcampos code e description")
                                    
                                    for unit_field, unit_data in sub_data.get("properties", {}).items():
                                        unit_field_name = f"amount_unit_{unit_field}"
                                        logger.info(f"Processando subcampo {unit_field_name} de unit em AmountDetails")
                                        
                                        # Calcula tamanho do subcampo
                                        unit_field_size = calculate_field_size(unit_field, unit_data)
                                        logger.info(f"Definindo tamanho {unit_field_size} para {unit_field_name} baseado no maior valor do enum")
                                        
                                        # Adiciona o subcampo u00e0 lista de propriedades
                                        processed_properties[unit_field_name] = {
                                            "type": "string",
                                            "maxLength": unit_field_size
                                        }
                                        
                                        logger.info(f"Incorporando subcampo {unit_field_name} de unit em AmountDetails com tamanho {unit_field_size}")
    
    # Processa cada propriedade do schema
    for prop_name, prop_data in processed_properties.items():
        try:
            # Ignora referu00eancias a outros schemas se for um schema de seguro
            if is_insurance_schema and "$ref" in prop_data:
                ref_value = prop_data["$ref"]
                # Se for uma referu00eancia a outro schema (nu00e3o AmountDetails), ignora
                if not ref_value.endswith("/AmountDetails"):
                    logger.info(f"Ignorando campo {prop_name} com referu00eancia a {ref_value.split('/')[-1]} (relacionamento via policyId)")
                    continue
            
            # Se o campo for um array com items que tem $ref, ignora se for schema de seguro
            if is_insurance_schema and prop_data.get("type") == "array" and "items" in prop_data and "$ref" in prop_data["items"]:
                ref_schema = prop_data["items"]["$ref"].split("/")[-1]
                logger.info(f"Ignorando campo {prop_name} com referu00eancia a {ref_schema} em array (relacionamento via policyId)")
                continue
                
            # Extrai tipo e tamanho do campo
            field_type = extract_field_type(prop_data)
            field_size = calculate_field_size(prop_name, prop_data)
            field_enum = prop_data.get("enum", [])
            field_required = prop_name in required_fields
            
            # Configura a regra de validau00e7u00e3o
            rule_config = {
                "type": field_type,
                "size": field_size,
                "required": field_required
            }
            
            # Inclui valores de enum se existirem
            if field_enum:
                rule_config["enum_values"] = field_enum
                
            # Persist no banco de dados
            upsert_regra_validacao(session, conjunto_id, prop_name, rule_config)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Erro ao processar campo {prop_name} do schema {schema_name}: {str(e)}")
    
    return processed_count


def extract_field_type(field_data: Dict[str, Any]) -> str:
    """
    Extrai o tipo de um campo do schema.
    
    Args:
        field_data: Dados do campo
        
    Returns:
        str: Tipo do campo (string, number, integer, boolean, etc.)
    """
    if "type" in field_data:
        return field_data["type"]
    elif "$ref" in field_data:
        # Para referu00eancias, assume string como padru00e3o
        return "string"
    else:
        # Tipo padru00e3o se nu00e3o for especificado
        return "string"


def calculate_field_size(field_name: str, field_data: Dict[str, Any]) -> int:
    """
    Calcula o tamanho adequado para um campo com base em suas caracteru00edsticas.
    
    Args:
        field_name: Nome do campo
        field_data: Dados do campo
        
    Returns:
        int: Tamanho calculado para o campo
    """
    field_type = extract_field_type(field_data)
    
    # Se for string, verifica o tamanho mu00e1ximo definido
    if field_type == "string":
        if "maxLength" in field_data:
            return field_data["maxLength"]
        elif "enum" in field_data:
            # Calcula baseado no maior valor do enum
            max_enum_length = max([len(str(e)) for e in field_data["enum"]]) if field_data["enum"] else 0
            logger.info(f"Definindo tamanho {max_enum_length} para campo {field_name} baseado no maior valor do enum (string)")
            return max_enum_length
        else:
            # Tamanho padru00e3o para strings sem tamanho definido
            size = 100
            logger.info(f"Definindo tamanho padru00e3o {size} para campo {field_name} (string sem ENUM ou tamanho definido)")
            return size
    
    # Para tipos numu00e9ricos
    elif field_type in ["number", "integer"]:
        # Tamanho padru00e3o para nu00fameros
        return 10
    
    # Para outros tipos (boolean, array, object)
    else:
        return 1  # Valor padru00e3o mu00ednimo