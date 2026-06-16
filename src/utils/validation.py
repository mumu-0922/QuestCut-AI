"""
Image Validation for QuestCut-AI
============================
Validates images before processing to prevent errors and crashes.
"""
import os
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from PIL import Image
logger = logging.getLogger(__name__)
class ValidationSeverity(Enum):
    """Severity level of validation issues."""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
@dataclass
class ValidationIssue:
    """A validation issue found with an image."""
    severity: ValidationSeverity
    code: str
    message: str
    details: Optional[str] = None
    suggestion: Optional[str] = None
    def __str__(self):
        result = f'[{self.severity.value.upper()}] {self.message}'
        if self.suggestion:
            result += f'\n  Suggestion: {self.suggestion}'
        return result
@dataclass
class ValidationResult:
    """Result of image validation."""
    valid: bool
    issues: List[ValidationIssue]
    image_info: Optional[dict] = None
    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)
    @property
    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    def get_error_message(self) -> str:
        """Get a formatted error message for display."""
        if not self.issues:
            return ''
        lines = []
        for issue in self.issues:
            lines.append(str(issue))
        return '\n\n'.join(lines)
class ImageValidator:
    """
    Validates images before processing.
    Checks:
    - File exists and is readable
    - File is a valid image format
    - Image dimensions are within limits
    - File size is reasonable
    - Image is not corrupted
    """
    MIN_DIMENSION = 32
    MAX_DIMENSION = 8192
    RECOMMENDED_MAX_DIMENSION = 4096
    MAX_FILE_SIZE = 104857600
    WARNING_FILE_SIZE = 52428800
    SUPPORTED_FORMATS = frozenset({
        '.webp', '.jpg', '.tiff', '.bmp', '.jpeg', '.png', '.gif'
    })
    def __init__(self):
        pass
    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Validate an image file.
        Args:
            file_path: Path to the image file
        Returns:
            ValidationResult with any issues found
        """
        issues = []
        image_info = None
        path = Path(file_path)
        if not path.exists():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code='FILE_NOT_FOUND',
                message=f'File not found: {path.name}',
                suggestion='Check that the file path is correct and the file exists.'
            ))
            return ValidationResult(valid=False, issues=issues)
        if not os.access(file_path, os.R_OK):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code='FILE_NOT_READABLE',
                message=f'Cannot read file: {path.name}',
                suggestion='Check file permissions or try running as administrator.'
            ))
            return ValidationResult(valid=False, issues=issues)
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code='UNSUPPORTED_FORMAT',
                message=f'Unsupported file format: {ext}',
                details=f'Supported formats: {", ".join(sorted(self.SUPPORTED_FORMATS))}',
                suggestion='Convert the image to PNG, JPEG, or WebP format.'
            ))
            return ValidationResult(valid=False, issues=issues)
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code='FILE_TOO_LARGE',
                message=f'File is too large: {file_size / 1048576:.1f} MB',
                details=f'Maximum allowed: {self.MAX_FILE_SIZE / 1048576:.0f} MB',
                suggestion='Resize the image to a smaller size before processing.'
            ))
            return ValidationResult(valid=False, issues=issues)
        if file_size > self.WARNING_FILE_SIZE:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code='FILE_LARGE',
                message=f'Large file: {file_size / 1048576:.1f} MB',
                details='Processing may be slow and use significant memory.',
                suggestion='Consider resizing for faster processing.'
            ))
        try:
            with Image.open(file_path) as img:
                img.verify()
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode
                format_name = img.format
                image_info = {
                    'width': width,
                    'height': height,
                    'mode': mode,
                    'format': format_name,
                    'file_size': file_size
                }
                if width < self.MIN_DIMENSION or height < self.MIN_DIMENSION:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code='IMAGE_TOO_SMALL',
                        message=f'Image too small: {width}×{height}',
                        details=f'Minimum dimensions: {self.MIN_DIMENSION}×{self.MIN_DIMENSION}',
                        suggestion='Use a larger image for better results.'
                    ))
                if width > self.MAX_DIMENSION or height > self.MAX_DIMENSION:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code='IMAGE_TOO_LARGE',
                        message=f'Image dimensions too large: {width}×{height}',
                        details=f'Maximum dimensions: {self.MAX_DIMENSION}×{self.MAX_DIMENSION}',
                        suggestion='Resize the image before processing.'
                    ))
                elif width > self.RECOMMENDED_MAX_DIMENSION or height > self.RECOMMENDED_MAX_DIMENSION:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code='IMAGE_LARGE_DIMENSIONS',
                        message=f'Large image: {width}×{height}',
                        details='Processing may be slow.',
                        suggestion=f'Consider resizing to {self.RECOMMENDED_MAX_DIMENSION}px for faster processing.'
                    ))
                aspect = max(width, height) / min(width, height)
                if aspect > 10:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code='EXTREME_ASPECT_RATIO',
                        message=f'Unusual aspect ratio: {aspect:.1f}:1',
                        details='Very wide or tall images may not process well.',
                        suggestion='Consider cropping to a more standard aspect ratio.'
                    ))
                if mode not in ('RGB', 'RGBA', 'L', 'LA', 'P'):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code='UNUSUAL_COLOR_MODE',
                        message=f'Unusual color mode: {mode}',
                        details='Image will be converted to RGB/RGBA.',
                        suggestion=None
                    ))
        except Image.UnidentifiedImageError:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code='INVALID_IMAGE',
                message='File is not a valid image',
                suggestion='The file may be corrupted or not an image file.'
            ))
            return ValidationResult(valid=False, issues=issues)
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code='IMAGE_READ_ERROR',
                message=f'Error reading image: {str(e)}',
                suggestion='The file may be corrupted. Try re-saving it in an image editor.'
            ))
            return ValidationResult(valid=False, issues=issues)
        valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        return ValidationResult(valid=valid, issues=issues, image_info=image_info)
    def validate_image(self, image: Image) -> ValidationResult:
        """
        Validate a PIL Image object.
        Args:
            image: PIL Image to validate
        Returns:
            ValidationResult with any issues found
        """
        issues = []
        width, height = image.size
        mode = image.mode
        image_info = {
            'width': width,
            'height': height,
            'mode': mode,
            'format': image.format
        }
        if width < self.MIN_DIMENSION or height < self.MIN_DIMENSION:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code='IMAGE_TOO_SMALL',
                message=f'Image too small: {width}×{height}',
                details=f'Minimum dimensions: {self.MIN_DIMENSION}×{self.MIN_DIMENSION}',
                suggestion='Use a larger image for better results.'
            ))
        if width > self.MAX_DIMENSION or height > self.MAX_DIMENSION:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code='IMAGE_TOO_LARGE',
                message=f'Image dimensions too large: {width}×{height}',
                details=f'Maximum dimensions: {self.MAX_DIMENSION}×{self.MAX_DIMENSION}',
                suggestion='Resize the image before processing.'
            ))
        elif width > self.RECOMMENDED_MAX_DIMENSION or height > self.RECOMMENDED_MAX_DIMENSION:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code='IMAGE_LARGE_DIMENSIONS',
                message=f'Large image: {width}×{height}',
                details='Processing may be slow.',
                suggestion=f'Consider resizing to {self.RECOMMENDED_MAX_DIMENSION}px for faster processing.'
            ))
        valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        return ValidationResult(valid=valid, issues=issues, image_info=image_info)
    def get_resize_recommendation(self, width: int, height: int,
                                   max_dimension: int = None) -> Tuple[int, int]:
        """
        Get recommended dimensions for resizing.
        Args:
            width: Current width
            height: Current height
            max_dimension: Maximum dimension (default: RECOMMENDED_MAX_DIMENSION)
        Returns:
            Recommended (width, height) tuple
        """
        if max_dimension is None:
            max_dimension = self.RECOMMENDED_MAX_DIMENSION
        if width <= max_dimension and height <= max_dimension:
            return (width, height)
        scale = min(max_dimension / width, max_dimension / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return (new_width, new_height)
_validator: Optional[ImageValidator] = None
def get_validator() -> ImageValidator:
    """Get the global validator instance."""
    global _validator
    if _validator is None:
        _validator = ImageValidator()
    return _validator
def validate_image_file(file_path: str) -> ValidationResult:
    """Convenience function to validate an image file."""
    return get_validator().validate_file(file_path)
def validate_image(image: Image) -> ValidationResult:
    """Convenience function to validate a PIL Image."""
    return get_validator().validate_image(image)
