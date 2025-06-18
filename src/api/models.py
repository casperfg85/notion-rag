from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class NotionObject(BaseModel):
    """Base Notion object"""
    object: str
    id: str
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None


class NotionParent(BaseModel):
    """Parent reference in Notion objects"""
    type: str
    page_id: Optional[str] = None
    database_id: Optional[str] = None
    block_id: Optional[str] = None
    workspace: Optional[bool] = None


class TextContent(BaseModel):
    """Text content within rich text"""
    content: str
    link: Optional[Dict[str, str]] = None


class MentionType(str, Enum):
    USER = "user"
    PAGE = "page"
    DATABASE = "database"
    DATE = "date"
    LINK_PREVIEW = "link_preview"
    TEMPLATE_MENTION = "template_mention"
    LINK_MENTION = "link_mention"


class MentionObject(BaseModel):
    """Mention object in rich text"""
    type: MentionType
    user: Optional[Dict[str, Any]] = None
    page: Optional[Dict[str, str]] = None
    database: Optional[Dict[str, str]] = None
    date: Optional[Dict[str, Any]] = None
    link_preview: Optional[Dict[str, str]] = None
    template_mention: Optional[Dict[str, str]] = None
    link_mention: Optional[Dict[str, str]] = None


class Annotations(BaseModel):
    """Text annotations"""
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False
    color: str = "default"


class EquationObject(BaseModel):
    """Equation object in rich text"""
    expression: str


class RichTextType(str, Enum):
    TEXT = "text"
    MENTION = "mention"
    EQUATION = "equation"


class RichTextObject(BaseModel):
    """Rich text object in Notion"""
    type: RichTextType
    text: Optional[TextContent] = None
    mention: Optional[MentionObject] = None
    equation: Optional[EquationObject] = None
    annotations: Annotations = Field(default_factory=Annotations)
    plain_text: str = ""
    href: Optional[str] = None


class FileType(str, Enum):
    FILE = "file"
    EXTERNAL = "external"


class FileAttachmentType(str, Enum):
    """Types of file attachments in Notion blocks"""
    FILE = "file"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    PDF = "pdf"


class InternalFile(BaseModel):
    """Internal file hosted by Notion"""
    url: str
    expiry_time: datetime


class ExternalFile(BaseModel):
    """External file reference"""
    url: str


class FileObject(BaseModel):
    """File object in Notion"""
    type: FileType
    file: Optional[InternalFile] = None
    external: Optional[ExternalFile] = None
    caption: List[RichTextObject] = Field(default_factory=list)
    name: Optional[str] = None


class BlockType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    BULLETED_LIST_ITEM = "bulleted_list_item"
    NUMBERED_LIST_ITEM = "numbered_list_item"
    TO_DO = "to_do"
    TOGGLE = "toggle"
    CODE = "code"
    CHILD_PAGE = "child_page"
    CHILD_DATABASE = "child_database"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"
    TABLE = "table"
    TABLE_ROW = "table_row"
    CALLOUT = "callout"
    QUOTE = "quote"
    DIVIDER = "divider"
    LINK_PREVIEW = "link_preview"
    SYNCED_BLOCK = "synced_block"
    BOOKMARK = "bookmark"
    EMBED = "embed"
    EQUATION = "equation"
    PDF = "pdf"
    AUDIO = "audio"
    BREADCRUMB = "breadcrumb"
    COLUMN = "column"
    COLUMN_LIST = "column_list"
    TEMPLATE = "template"
    TABLE_OF_CONTENTS = "table_of_contents"
    UNSUPPORTED = "unsupported"


class UserObject(BaseModel):
    """User object reference"""
    object: Literal["user"]
    id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    type: Optional[str] = None
    person: Optional[Dict[str, Any]] = None
    bot: Optional[Dict[str, Any]] = None


class RichTextBlock(BaseModel):
    """Block content with rich text"""
    rich_text: List[RichTextObject] = Field(default_factory=list)
    color: str = "default"


class HeadingBlock(RichTextBlock):
    """Heading block content"""
    is_toggleable: bool = False


class ListItemBlock(RichTextBlock):
    """List item block content"""
    children: Optional[List[Dict[str, Any]]] = None


class ToDoBlock(RichTextBlock):
    """To-do block content"""
    checked: bool = False
    children: Optional[List[Dict[str, Any]]] = None


class CodeBlock(BaseModel):
    """Code block content"""
    rich_text: List[RichTextObject] = Field(default_factory=list)
    caption: List[RichTextObject] = Field(default_factory=list)
    language: str = "plain text"


class CalloutBlock(RichTextBlock):
    """Callout block content"""
    icon: Optional[Dict[str, Any]] = None
    children: Optional[List[Dict[str, Any]]] = None


class ChildPageBlock(BaseModel):
    """Child page block content"""
    title: str


class ChildDatabaseBlock(BaseModel):
    """Child database block content"""
    title: str


class TableBlock(BaseModel):
    """Table block content"""
    table_width: int
    has_column_header: bool = False
    has_row_header: bool = False
    children: Optional[List[Dict[str, Any]]] = None


class TableRowBlock(BaseModel):
    """Table row block content"""
    cells: List[List[RichTextObject]] = Field(default_factory=list)


class LinkPreviewBlock(BaseModel):
    """Link preview block content"""
    url: str


class SyncedFromBlock(BaseModel):
    """Synced from block reference"""
    block_id: Optional[str] = None


class SyncedBlock(BaseModel):
    """Synced block content"""
    synced_from: Optional[SyncedFromBlock] = None
    children: Optional[List[Dict[str, Any]]] = None


class BookmarkBlock(BaseModel):
    """Bookmark block content"""
    url: str
    caption: List[RichTextObject] = Field(default_factory=list)


class EmbedBlock(BaseModel):
    """Embed block content"""
    url: str
    caption: List[RichTextObject] = Field(default_factory=list)


class EquationBlock(BaseModel):
    """Equation block content"""
    expression: str


class NotionBlock(NotionObject):
    """Notion block object"""
    type: BlockType
    has_children: bool
    archived: bool
    parent: Optional[NotionParent] = None
    created_by: Optional[UserObject] = None
    last_edited_by: Optional[UserObject] = None
    
    # Block-specific content (dynamic based on type)
    paragraph: Optional[RichTextBlock] = None
    heading_1: Optional[HeadingBlock] = None
    heading_2: Optional[HeadingBlock] = None
    heading_3: Optional[HeadingBlock] = None
    bulleted_list_item: Optional[ListItemBlock] = None
    numbered_list_item: Optional[ListItemBlock] = None
    to_do: Optional[ToDoBlock] = None
    toggle: Optional[ListItemBlock] = None
    code: Optional[CodeBlock] = None
    child_page: Optional[ChildPageBlock] = None
    child_database: Optional[ChildDatabaseBlock] = None
    image: Optional[FileObject] = None
    file: Optional[FileObject] = None
    video: Optional[FileObject] = None
    audio: Optional[FileObject] = None
    pdf: Optional[FileObject] = None
    table: Optional[TableBlock] = None
    table_row: Optional[TableRowBlock] = None
    callout: Optional[CalloutBlock] = None
    quote: Optional[RichTextBlock] = None
    divider: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Empty object
    link_preview: Optional[LinkPreviewBlock] = None
    synced_block: Optional[SyncedBlock] = None
    bookmark: Optional[BookmarkBlock] = None
    embed: Optional[EmbedBlock] = None
    equation: Optional[EquationBlock] = None
    breadcrumb: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Empty object
    column: Optional[Dict[str, Any]] = None
    column_list: Optional[Dict[str, Any]] = None
    template: Optional[Dict[str, Any]] = None
    table_of_contents: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Empty object
    unsupported: Optional[Dict[str, Any]] = None


class IconType(str, Enum):
    EMOJI = "emoji"
    EXTERNAL = "external"
    FILE = "file"


class IconObject(BaseModel):
    """Icon object for pages and databases"""
    type: IconType
    emoji: Optional[str] = None
    external: Optional[ExternalFile] = None
    file: Optional[InternalFile] = None


class PropertyType(str, Enum):
    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    PEOPLE = "people"
    FILES = "files"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    FORMULA = "formula"
    RELATION = "relation"
    ROLLUP = "rollup"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"
    STATUS = "status"
    UNIQUE_ID = "unique_id"


class SelectOption(BaseModel):
    """Select option object"""
    id: str
    name: str
    color: str


class DateObject(BaseModel):
    """Date object in properties"""
    start: str  # ISO 8601 date string
    end: Optional[str] = None
    time_zone: Optional[str] = None


class FormulaResult(BaseModel):
    """Formula result object"""
    type: str
    string: Optional[str] = None
    number: Optional[float] = None
    boolean: Optional[bool] = None
    date: Optional[DateObject] = None


class RelationObject(BaseModel):
    """Relation object"""
    id: str


class RollupResult(BaseModel):
    """Rollup result object"""
    type: str
    number: Optional[float] = None
    date: Optional[DateObject] = None
    array: Optional[List[Dict[str, Any]]] = None
    incomplete: bool = False


class UniqueIdObject(BaseModel):
    """Unique ID object"""
    number: int
    prefix: Optional[str] = None


class PropertyValue(BaseModel):
    """Base property value"""
    id: str
    type: PropertyType
    

class TitleProperty(PropertyValue):
    """Title property value"""
    title: List[RichTextObject] = Field(default_factory=list)


class RichTextProperty(PropertyValue):
    """Rich text property value"""
    rich_text: List[RichTextObject] = Field(default_factory=list)


class NumberProperty(PropertyValue):
    """Number property value"""
    number: Optional[float] = None


class SelectProperty(PropertyValue):
    """Select property value"""
    select: Optional[SelectOption] = None


class MultiSelectProperty(PropertyValue):
    """Multi-select property value"""
    multi_select: List[SelectOption] = Field(default_factory=list)


class DateProperty(PropertyValue):
    """Date property value"""
    date: Optional[DateObject] = None


class PeopleProperty(PropertyValue):
    """People property value"""
    people: List[UserObject] = Field(default_factory=list)


class FilesProperty(PropertyValue):
    """Files property value"""
    files: List[FileObject] = Field(default_factory=list)


class CheckboxProperty(PropertyValue):
    """Checkbox property value"""
    checkbox: bool = False


class UrlProperty(PropertyValue):
    """URL property value"""
    url: Optional[str] = None


class EmailProperty(PropertyValue):
    """Email property value"""
    email: Optional[str] = None


class PhoneNumberProperty(PropertyValue):
    """Phone number property value"""
    phone_number: Optional[str] = None


class FormulaProperty(PropertyValue):
    """Formula property value"""
    formula: FormulaResult


class RelationProperty(PropertyValue):
    """Relation property value"""
    relation: List[RelationObject] = Field(default_factory=list)
    has_more: bool = False


class RollupProperty(PropertyValue):
    """Rollup property value"""
    rollup: RollupResult


class CreatedTimeProperty(PropertyValue):
    """Created time property value"""
    created_time: datetime


class CreatedByProperty(PropertyValue):
    """Created by property value"""
    created_by: UserObject


class LastEditedTimeProperty(PropertyValue):
    """Last edited time property value"""
    last_edited_time: datetime


class LastEditedByProperty(PropertyValue):
    """Last edited by property value"""
    last_edited_by: UserObject


class StatusProperty(PropertyValue):
    """Status property value"""
    status: Optional[SelectOption] = None


class UniqueIdProperty(PropertyValue):
    """Unique ID property value"""
    unique_id: UniqueIdObject


class NotionPage(NotionObject):
    """Notion page object"""
    parent: NotionParent
    archived: bool
    properties: Dict[str, PropertyValue]
    url: str
    public_url: Optional[str] = None
    created_by: Optional[UserObject] = None
    last_edited_by: Optional[UserObject] = None
    cover: Optional[FileObject] = None
    icon: Optional[IconObject] = None


class DatabasePropertySchema(BaseModel):
    """Database property schema definition"""
    id: str
    name: str
    type: PropertyType
    
    # Type-specific configurations
    title: Optional[Dict[str, Any]] = None
    rich_text: Optional[Dict[str, Any]] = None
    number: Optional[Dict[str, str]] = None  # format
    select: Optional[Dict[str, List[SelectOption]]] = None  # options
    multi_select: Optional[Dict[str, List[SelectOption]]] = None  # options
    date: Optional[Dict[str, Any]] = None
    people: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None
    checkbox: Optional[Dict[str, Any]] = None
    url: Optional[Dict[str, Any]] = None
    email: Optional[Dict[str, Any]] = None
    phone_number: Optional[Dict[str, Any]] = None
    formula: Optional[Dict[str, str]] = None  # expression
    relation: Optional[Dict[str, Any]] = None
    rollup: Optional[Dict[str, Any]] = None
    created_time: Optional[Dict[str, Any]] = None
    created_by: Optional[Dict[str, Any]] = None
    last_edited_time: Optional[Dict[str, Any]] = None
    last_edited_by: Optional[Dict[str, Any]] = None
    status: Optional[Dict[str, List[SelectOption]]] = None  # options
    unique_id: Optional[Dict[str, str]] = None  # prefix


class NotionDatabase(NotionObject):
    """Notion database object"""
    title: List[RichTextObject] = Field(default_factory=list)
    description: List[RichTextObject] = Field(default_factory=list)
    properties: Dict[str, DatabasePropertySchema]
    parent: NotionParent
    url: str
    archived: bool
    is_inline: bool
    public_url: Optional[str] = None
    created_by: Optional[UserObject] = None
    last_edited_by: Optional[UserObject] = None
    cover: Optional[FileObject] = None
    icon: Optional[IconObject] = None


class NotionBlockList(BaseModel):
    """Response from blocks.children.list"""
    object: str
    results: List[NotionBlock]
    next_cursor: Optional[str] = None
    has_more: bool
    type: str = 'block'


class NotionDatabaseQuery(BaseModel):
    """Response from databases.query"""
    object: str
    results: List[NotionPage]
    next_cursor: Optional[str] = None
    has_more: bool
    type: str = 'page'