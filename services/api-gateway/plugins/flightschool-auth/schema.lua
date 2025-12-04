-- services/api-gateway/plugins/flightschool-auth/schema.lua
-- Plugin configuration schema

local typedefs = require "kong.db.schema.typedefs"

return {
    name = "flightschool-auth",
    fields = {
        { consumer = typedefs.no_consumer },
        { protocols = typedefs.protocols_http },
        { config = {
            type = "record",
            fields = {
                -- JWT Configuration
                {
                    jwt_secret = {
                        type = "string",
                        required = false,
                        default = nil,
                        encrypted = true,
                        description = "Secret for HS256 JWT validation (if not using RS256)"
                    }
                },
                {
                    jwt_public_key = {
                        type = "string",
                        required = false,
                        default = nil,
                        description = "Public key for RS256 JWT validation"
                    }
                },
                {
                    jwt_algorithm = {
                        type = "string",
                        required = true,
                        default = "RS256",
                        one_of = { "HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512" },
                        description = "JWT signing algorithm"
                    }
                },

                -- Token Settings
                {
                    token_header = {
                        type = "string",
                        required = true,
                        default = "Authorization",
                        description = "Header name for JWT token"
                    }
                },
                {
                    token_prefix = {
                        type = "string",
                        required = true,
                        default = "Bearer",
                        description = "Token prefix (e.g., Bearer)"
                    }
                },

                -- Validation Settings
                {
                    verify_exp = {
                        type = "boolean",
                        required = true,
                        default = true,
                        description = "Verify token expiration"
                    }
                },
                {
                    verify_nbf = {
                        type = "boolean",
                        required = true,
                        default = true,
                        description = "Verify token not-before claim"
                    }
                },
                {
                    verify_iss = {
                        type = "boolean",
                        required = true,
                        default = true,
                        description = "Verify token issuer"
                    }
                },
                {
                    expected_issuer = {
                        type = "string",
                        required = false,
                        default = "flightschool-auth",
                        description = "Expected token issuer"
                    }
                },

                -- Caching
                {
                    cache_ttl = {
                        type = "number",
                        required = true,
                        default = 300,
                        gt = 0,
                        description = "Token cache TTL in seconds"
                    }
                },

                -- Public Paths (paths that don't require auth)
                {
                    public_paths = {
                        type = "array",
                        required = false,
                        default = {
                            "/api/v1/auth/login",
                            "/api/v1/auth/register",
                            "/api/v1/auth/forgot-password",
                            "/api/v1/auth/reset-password",
                            "/api/v1/auth/verify-email",
                            "/api/v1/auth/refresh",
                            "/health",
                            "/share/"
                        },
                        elements = { type = "string" },
                        description = "Paths that don't require authentication"
                    }
                },

                -- Required Claims
                {
                    required_claims = {
                        type = "array",
                        required = false,
                        default = { "sub", "org_id" },
                        elements = { type = "string" },
                        description = "Required JWT claims"
                    }
                },

                -- Header Mapping (JWT claim -> upstream header)
                {
                    claim_headers = {
                        type = "map",
                        required = false,
                        default = {
                            sub = "X-User-ID",
                            org_id = "X-Organization-ID",
                            email = "X-User-Email",
                            name = "X-User-Name"
                        },
                        keys = { type = "string" },
                        values = { type = "string" },
                        description = "Mapping of JWT claims to upstream headers"
                    }
                },

                -- Error Messages
                {
                    anonymous_on_error = {
                        type = "boolean",
                        required = true,
                        default = false,
                        description = "Allow anonymous access on auth errors"
                    }
                }
            }
        }}
    }
}
