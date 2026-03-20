#!/usr/bin/env python3
"""
Protobuf compatibility fix - must be imported FIRST before any TensorFlow imports
"""

import os
import sys

# Set environment variables BEFORE any other imports
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Fix protobuf runtime_version compatibility issue
try:
    import google.protobuf
    
    # Check if runtime_version exists, if not create a mock
    if not hasattr(google.protobuf, 'runtime_version'):
        # Create a mock runtime_version module with all required attributes
        class MockDomain:
            PUBLIC = "PUBLIC"
            GOOGLE_INTERNAL = "GOOGLE_INTERNAL"
        
        class MockRuntimeVersion:
            def __init__(self):
                self.PROTOBUF_VERSION = getattr(google.protobuf, '__version__', '4.25.0')
                self.Domain = MockDomain()
                
            def ValidateProtobufRuntimeVersion(self, *args, **kwargs):
                return True
        
        google.protobuf.runtime_version = MockRuntimeVersion()
        print("✅ Applied protobuf runtime_version compatibility fix")
    
    PROTOBUF_AVAILABLE = True
    
    # Suppress protobuf warnings
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')
    warnings.filterwarnings('ignore', message='.*protobuf.*')
    print("✅ Protobuf compatibility fix applied successfully")
    
except ImportError as e:
    PROTOBUF_AVAILABLE = False
    print(f"Warning: google.protobuf not installed: {e}. TensorFlow features will be disabled.")