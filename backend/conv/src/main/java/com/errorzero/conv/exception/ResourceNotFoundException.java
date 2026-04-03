package com.errorzero.conv.exception;

/**
 * 요청한 리소스를 찾을 수 없을 때 발생하는 예외.
 */
public class ResourceNotFoundException extends RuntimeException {

    public ResourceNotFoundException(String message) {
        super(message);
    }

    public ResourceNotFoundException(String resourceName, String fieldName, Object fieldValue) {
        super(String.format("%s을(를) 찾을 수 없습니다. [%s: %s]", resourceName, fieldName, fieldValue));
    }
}
