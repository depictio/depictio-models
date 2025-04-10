from beanie import init_beanie, PydanticObjectId
from datetime import datetime, timedelta
from mongomock_motor import AsyncMongoMockClient
from pydantic import ValidationError
import pytest

from depictio_models.models.users import TokenData, Token, TokenBeanie, TokenBase


# Example of a test using AsyncMongoMockClient
# class Data(Document):
#     value: int

#     class Settings:
#         name = "data"

#     @pytest.mark.asyncio
#     async def test_beanie_sort():
#         client = AsyncMongoMockClient()
#         await init_beanie(database=client.beanie_test, document_models=[Data])

#         values = [2, 0, 4, 3, 1]
#         await client.beanie_test.data.insert_many([{"value": i} for i in values])

#         result = await Data.find().sort(str(Data.value)).to_list()
#         assert [v.value for v in result] == sorted(values)

#         result = await Data.find().sort(Data.value).to_list()
#         assert [v.value for v in result] == sorted(values)


class TestTokenData:
    def test_token_data_default_creation(self):
        """Test creating TokenData with default values."""
        sub = PydanticObjectId()
        token_data = TokenData(sub=sub)

        assert token_data.name is None
        assert token_data.token_lifetime == "short-lived"
        assert token_data.token_type == "bearer"
        assert str(token_data.sub) == str(sub)

    def test_token_data_custom_creation(self):
        """Test creating TokenData with custom values."""
        sub = PydanticObjectId()
        token_data = TokenData(
            name="Test User", token_lifetime="long-lived", token_type="custom", sub=sub
        )

        assert token_data.name == "Test User"
        assert token_data.token_lifetime == "long-lived"
        assert token_data.token_type == "custom"
        assert str(token_data.sub) == str(sub)

    def test_token_data_invalid_lifetime(self):
        """Test validation of token lifetime."""
        sub = PydanticObjectId()
        with pytest.raises(ValidationError) as exc_info:
            TokenData(sub=sub, token_lifetime="invalid-lifetime")

        # Check that the error is related to pattern mismatch
        assert any(
            error.get("type") == "string_pattern_mismatch" for error in exc_info.value.errors()
        )

        # Optional: more detailed error checking
        error_messages = [error.get("msg") for error in exc_info.value.errors()]
        assert any("pattern" in msg for msg in error_messages)

    def test_token_data_invalid_type(self):
        """Test validation of token type."""
        sub = PydanticObjectId()
        with pytest.raises(ValidationError) as exc_info:
            TokenData(sub=sub, token_type="invalid-type")

        # Check that the error is related to pattern mismatch
        assert any(
            error.get("type") == "string_pattern_mismatch" for error in exc_info.value.errors()
        )

        # Optional: more detailed error checking
        error_messages = [error.get("msg") for error in exc_info.value.errors()]
        assert any("pattern" in msg for msg in error_messages)


class TestToken:
    def test_token_creation(self):
        """Test creating a complete Token instance."""
        sub = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        token = Token(access_token="ValidToken123", expire_datetime=future_time, sub=sub)

        assert token.access_token == "ValidToken123"
        assert token.expire_datetime == future_time
        assert str(token.sub) == str(sub)
        assert token.token_lifetime == "short-lived"
        assert token.token_type == "bearer"

    def test_token_invalid_expiration(self):
        """Test validation of token expiration."""
        sub = PydanticObjectId()

        # Past datetime
        past_time = datetime.now() - timedelta(hours=1)
        with pytest.raises(ValidationError, match="Expiration datetime must be in the future"):
            Token(access_token="ValidToken123", expire_datetime=past_time, sub=sub)

    def test_token_invalid_access_token(self):
        """Test validation of access token."""
        sub = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        # Token without mix of characters
        with pytest.raises(
            ValidationError,
            match="Access token must contain uppercase, lowercase, and numeric characters",
        ):
            Token(access_token="lowercase_only", expire_datetime=future_time, sub=sub)

        # Token too short
        with pytest.raises(ValidationError):
            Token(access_token="Short1", expire_datetime=future_time, sub=sub)

    def test_token_serialization(self):
        """Test serialization of Token model."""
        sub = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        token = Token(access_token="ValidToken123", expire_datetime=future_time, sub=sub)

        # Test JSON serialization
        token_dict = token.model_dump()
        assert isinstance(token_dict["sub"], str)
        assert isinstance(token_dict["expire_datetime"], str)

        # Verify ISO format for datetime
        assert token_dict["expire_datetime"] == future_time.isoformat()


# ---------------------------------
# Tests for TokenBeanie
# ---------------------------------


@pytest.mark.asyncio
class TestTokenBeanie:
    async def test_token_beanie_creation(self):
        """Test creating and inserting a TokenBeanie document."""
        # Initialize Beanie directly in the test
        client = AsyncMongoMockClient()
        await init_beanie(database=client.test_db, document_models=[TokenBeanie])

        user_id = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        # Create a token instance
        token = TokenBeanie(
            user_id=user_id,
            access_token="test_access_token",
            expire_datetime=future_time,
            name="test_token",
        )

        # Insert the document
        await token.save()

        # Retrieve the document
        retrieved_token = await TokenBeanie.find_one(TokenBeanie.user_id == user_id)

        assert retrieved_token is not None
        assert retrieved_token.user_id == user_id
        assert retrieved_token.access_token == "test_access_token"
        assert retrieved_token.token_type == "bearer"
        assert retrieved_token.token_lifetime == "short-lived"
        assert retrieved_token.name == "test_token"
        # Check expire_datetime is approximately the same (allowing for millisecond differences)
        assert abs((retrieved_token.expire_datetime - future_time).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_token_beanie_multiple_tokens(self):
        """Test creating and retrieving multiple tokens."""
        # Initialize Beanie directly in the test
        client = AsyncMongoMockClient()
        await init_beanie(database=client.test_db, document_models=[TokenBeanie])

        user_id1 = PydanticObjectId()
        user_id2 = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        # Create two tokens for different users
        token1 = TokenBeanie(
            user_id=user_id1,
            access_token="token1_access_token",
            expire_datetime=future_time,
            name="token1",
        )
        token2 = TokenBeanie(
            user_id=user_id2,
            access_token="token2_access_token",
            expire_datetime=future_time,
            name="token2",
        )

        await token1.save()
        await token2.save()

        # Retrieve tokens using Beanie's query interface
        retrieved_tokens = await TokenBeanie.find(
            {"user_id": {"$in": [user_id1, user_id2]}}
        ).to_list()

        assert len(retrieved_tokens) == 2

        # Convert ObjectIds to strings for comparison
        retrieved_user_ids = [str(token.user_id) for token in retrieved_tokens]
        assert str(user_id1) in retrieved_user_ids
        assert str(user_id2) in retrieved_user_ids

        # Test filtering by user_id for a single user
        user1_tokens = await TokenBeanie.find({"user_id": user_id1}).to_list()
        assert len(user1_tokens) == 1
        assert str(user1_tokens[0].user_id) == str(user_id1)

    @pytest.mark.asyncio
    async def test_token_to_response_dict(self):
        """Test the to_response_dict method."""
        # Initialize Beanie directly in the test
        client = AsyncMongoMockClient()
        await init_beanie(database=client.test_db, document_models=[TokenBeanie])

        user_id = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        token = TokenBeanie(
            user_id=user_id,
            access_token="test_access_token",
            expire_datetime=future_time,
            name="test_token",
        )

        await token.save()

        # Get the response dict
        response_dict = token.model_dump()
        print(f"Response dict: {response_dict}")

        # Verify the fields in the response dict
        assert "id" in response_dict
        assert "user_id" in response_dict
        assert "access_token" in response_dict
        assert "token_type" in response_dict
        assert "expire_datetime" in response_dict
        assert "created_at" in response_dict

        # Check values
        assert response_dict["user_id"] == str(user_id)
        assert response_dict["access_token"] == "test_access_token"
        assert response_dict["token_type"] == "bearer"
        # expires_in should be close to 3600 seconds (1 hour)
        # convert datetime to seconds
        print(f"Expire datetime: {response_dict['expire_datetime']}")
        # Convert datetime back to datetime object
        expire_datetime = datetime.fromisoformat(response_dict["expire_datetime"])
        print(f"Expire datetime: {expire_datetime}")
        # Calculate the difference in seconds
        expire_in_secs = int((expire_datetime - datetime.now()).total_seconds())
        # expire_in_secs = int((response_dict["expire_datetime"] - datetime.now()).total_seconds())
        print(f"Expire in seconds: {expire_in_secs}")
        assert 3500 < expire_in_secs < 3600

    @pytest.mark.asyncio
    async def test_token_expiration(self):
        """Test querying tokens based on expiration."""
        # Initialize Beanie directly in the test
        client = AsyncMongoMockClient()
        await init_beanie(database=client.test_db, document_models=[TokenBeanie])

        user_id = PydanticObjectId()

        # Create an expired token
        past_time = datetime.now() - timedelta(hours=1)
        expired_token = TokenBeanie(
            user_id=user_id,
            access_token="expired_token",
            expire_datetime=past_time,
            name="expired_token",
        )

        # Create a valid token
        future_time = datetime.now() + timedelta(hours=1)
        valid_token = TokenBeanie(
            user_id=user_id,
            access_token="valid_token",
            expire_datetime=future_time,
            name="valid_token",
        )

        await expired_token.save()
        await valid_token.save()

        # Find valid tokens (not expired)
        current_time = datetime.now()
        valid_tokens = await TokenBeanie.find({"expire_datetime": {"$gt": current_time}}).to_list()

        # Should find only the valid token
        assert len(valid_tokens) == 1
        assert valid_tokens[0].access_token == "valid_token"

        # Find expired tokens
        expired_tokens = await TokenBeanie.find(
            {"expire_datetime": {"$lt": current_time}}
        ).to_list()

        # Should find only the expired token
        assert len(expired_tokens) == 1
        assert expired_tokens[0].access_token == "expired_token"


# ---------------------
# Tests for TokenBase
# ---------------------


class TestTokenBase:
    def test_token_base_creation(self):
        """Test creating a complete TokenBase instance."""
        user_id = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        token_base = TokenBase(
            user_id=user_id,
            access_token="ValidToken123",
            expire_datetime=future_time,
            name="Test Token",
        )

        assert token_base.user_id == user_id
        assert token_base.access_token == "ValidToken123"
        assert token_base.expire_datetime == future_time
        assert token_base.name == "Test Token"
        assert token_base.token_type == "bearer"
        assert token_base.token_lifetime == "short-lived"
        assert token_base.logged_in is False

    def test_token_base_serializers(self):
        """Test serialization methods of TokenBase."""
        user_id = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)
        creation_time = datetime.now()

        token_base = TokenBase(
            user_id=user_id,
            access_token="ValidToken123",
            expire_datetime=future_time,
            created_at=creation_time,
        )

        # Test id serializer if applicable
        if hasattr(token_base, "id"):
            assert isinstance(token_base.serialize_id(token_base.id), str)

        # Test user_id serializer
        assert isinstance(token_base.serialize_user_id(user_id), str)

        # Test datetime serializers
        assert token_base.serialize_expire_datetime(future_time) == future_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        assert token_base.serialize_created_at(creation_time) == creation_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def test_to_response_dict(self):
        """Test the to_response_dict method returns correct format."""
        user_id = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        token_base = TokenBase(
            user_id=user_id, access_token="ValidToken123", expire_datetime=future_time
        )

        response = token_base.to_response_dict()

        assert "id" in response
        assert "user_id" in response
        assert "access_token" in response
        assert "token_type" in response
        assert "expires_in" in response
        assert "expires_at" in response
        assert "created_at" in response

        # Check that expires_in is calculated correctly
        assert isinstance(response["expires_in"], int)
        # Allow 1 second tolerance for test execution time
        expected_seconds = int((future_time - datetime.now()).total_seconds())
        assert abs(response["expires_in"] - expected_seconds) <= 1

        assert str(response["user_id"]) == str(user_id)
        assert response["access_token"] == "ValidToken123"
        assert response["token_type"] == "bearer"

    def test_default_values(self):
        """Test default values are set correctly."""
        user_id = PydanticObjectId()
        future_time = datetime.now() + timedelta(hours=1)

        token_base = TokenBase(
            user_id=user_id, access_token="ValidToken123", expire_datetime=future_time
        )

        assert token_base.token_type == "bearer"
        assert token_base.token_lifetime == "short-lived"
        assert token_base.logged_in is False
        assert token_base.name is None
        assert isinstance(token_base.created_at, datetime)
