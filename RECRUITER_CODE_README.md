# Recruiter Code Feature Implementation

This document describes the implementation of the recruiter code feature that allows students to link to recruiters and access their assessments.

## Overview

The recruiter code feature enables:
- Recruiters to have unique, shareable codes
- Students to link to recruiters using these codes
- Automatic access to all assessments from linked recruiters
- Email invitation links that include recruiter codes for auto-linking

## Database Changes

### New Column Added
- **Table**: `users`
- **Column**: `recruiter_code`
- **Type**: `VARCHAR`
- **Constraints**: `UNIQUE`, `NULLABLE`, `INDEXED`

### Migration
Run the migration script to add the column to existing databases:
```bash
python add_recruiter_code_column.py
```

## Backend Implementation

### New API Endpoints

#### 1. Validate Recruiter Code
```
POST /api/v1/recruiter-code/validate
```
**Request Body:**
```json
{
  "recruiter_code": "ABC12345"
}
```
**Response:**
```json
{
  "is_valid": true,
  "recruiter_name": "John Doe",
  "recruiter_id": 123,
  "message": "Valid recruiter code."
}
```

#### 2. Link Student to Recruiter
```
POST /api/v1/recruiter-code/link
```
**Request Body:**
```json
{
  "recruiter_code": "ABC12345"
}
```
**Response:**
```json
{
  "message": "Successfully linked to John Doe",
  "recruiter_name": "John Doe",
  "recruiter_id": 123,
  "linked_assessments": [...]
}
```

#### 3. Get Student's Recruiter Info
```
GET /api/v1/recruiter-code/my-recruiter
```

#### 4. Get Recruiter's Assessments for Student
```
GET /api/v1/recruiter-code/recruiter-assessments
```

### New Services

#### UserService Methods
- `generate_recruiter_code(db)`: Generates unique 8-character alphanumeric codes
- `validate_recruiter_code(db, code)`: Validates recruiter codes
- `link_student_to_recruiter(db, student_id, recruiter_id)`: Links students to recruiters
- `get_recruiter_assessments_for_student(db, student_id, recruiter_id)`: Gets recruiter's assessments

### Automatic Code Generation
- New users with `Admin` or `Recruiter` roles automatically get recruiter codes
- Existing admin/recruiter users get codes generated during migration

## Frontend Implementation

### Student Dashboard Updates

#### New UI Elements
1. **Recruiter Code Button**: Added to sidebar
2. **Recruiter Code Modal**: Input field for entering codes
3. **Recruiter Info Display**: Shows linked recruiter information
4. **Assessment Integration**: Combines regular and recruiter assessments

#### Modal Features
- **Validation**: Real-time code validation
- **Linking**: Secure linking to recruiters
- **Success Feedback**: Clear confirmation messages
- **Error Handling**: User-friendly error messages

### URL Parameter Handling

#### Auto-linking via Email
- Email links now include `?recruiter_code=XXXX` parameter
- Students clicking email links are automatically linked to recruiters
- No manual code entry required for email invitations

#### Deep Linking Support
- Recruiter codes in URLs are processed automatically
- Students can share recruiter codes via direct links
- Seamless integration with existing authentication flow

## Email Integration

### Updated Email Templates
- Invitation emails now include recruiter codes
- Links automatically populate recruiter codes for easy access
- Clear instructions about auto-linking functionality

### Email Link Format
```
http://localhost:8501/?invite=TOKEN&recruiter_code=ABC12345
```

## Usage Flow

### For Recruiters
1. Recruiter creates account (gets unique code automatically)
2. Recruiter creates assessments
3. Recruiter invites students via email
4. Students receive emails with recruiter codes

### For Students
1. Student receives email invitation
2. Student clicks email link (auto-links to recruiter)
3. OR student manually enters recruiter code in dashboard
4. Student gains access to all recruiter's assessments
5. Student can take assessments and view progress

## Security Features

### Code Generation
- 8-character alphanumeric codes
- Unique constraint prevents duplicates
- Secure random generation using `secrets` module

### Access Control
- Only students can link to recruiters
- Validation before linking
- Prevention of duplicate links
- Role-based endpoint protection

## Error Handling

### Common Scenarios
- Invalid recruiter codes
- Already linked students
- Expired or used codes
- Network failures
- Database errors

### User Feedback
- Clear success messages
- Descriptive error messages
- Loading states during operations
- Automatic page refresh after linking

## Testing

### Backend Testing
- API endpoint validation
- Database constraint testing
- Error scenario testing
- Authentication testing

### Frontend Testing
- UI component rendering
- User interaction flows
- Error message display
- Integration with backend APIs

## Deployment Notes

### Database Migration
1. Run migration script: `python add_recruiter_code_column.py`
2. Verify column addition: `\d users` (PostgreSQL)
3. Check existing admin users have codes

### Application Updates
1. Deploy updated models and services
2. Restart FastAPI application
3. Update frontend application
4. Test email functionality

### Environment Variables
No new environment variables required. Uses existing database and email configurations.

## Troubleshooting

### Common Issues
1. **Migration fails**: Check database permissions and connection
2. **Codes not generating**: Verify user roles are correct
3. **Linking fails**: Check database constraints and relationships
4. **Email links not working**: Verify frontend URL configuration

### Debug Steps
1. Check application logs for errors
2. Verify database schema changes
3. Test API endpoints directly
4. Check frontend console for JavaScript errors

## Future Enhancements

### Potential Improvements
1. **Code Management**: Allow recruiters to regenerate codes
2. **Bulk Operations**: Link multiple students at once
3. **Analytics**: Track code usage and effectiveness
4. **Expiration**: Add time limits to recruiter codes
5. **Notifications**: Alert recruiters when students link

### Scalability Considerations
- Database indexing on recruiter_code
- Caching for frequently accessed recruiter data
- Rate limiting for code validation endpoints
- Monitoring for code generation conflicts

## Support

For issues or questions about the recruiter code feature:
1. Check application logs
2. Verify database schema
3. Test API endpoints
4. Review this documentation
5. Contact development team

