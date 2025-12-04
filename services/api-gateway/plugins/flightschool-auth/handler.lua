-- services/api-gateway/plugins/flightschool-auth/handler.lua
-- FlightSchool Custom Authentication Plugin for Kong
-- Handles JWT validation and user context propagation

local kong = kong
local jwt_decoder = require "kong.plugins.jwt.jwt_parser"
local cjson = require "cjson.safe"
local http = require "resty.http"

local FlightSchoolAuthHandler = {
    VERSION = "1.0.0",
    PRIORITY = 1005,  -- Run after rate-limiting, before request-transformer
}

-- =============================================================================
-- CONFIGURATION
-- =============================================================================

local PUBLIC_PATHS = {
    -- Auth endpoints (no token required)
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/refresh",
    -- Health checks
    "/health",
    "/api/v1/health",
    -- Public share links
    "/share/",
    -- OpenAPI docs
    "/api/docs",
    "/api/schema",
    "/api/redoc",
}

local CACHE_TTL = 300  -- 5 minutes token cache

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

local function is_public_path(path)
    for _, public_path in ipairs(PUBLIC_PATHS) do
        if path == public_path or path:sub(1, #public_path) == public_path then
            return true
        end
    end
    return false
end

local function extract_token(auth_header)
    if not auth_header then
        return nil, "Missing Authorization header"
    end

    local token = auth_header:match("Bearer%s+(.+)")
    if not token then
        return nil, "Invalid Authorization header format. Expected: Bearer <token>"
    end

    return token, nil
end

local function decode_jwt(token)
    local jwt, err = jwt_decoder:new(token)
    if err then
        return nil, "Invalid token format: " .. tostring(err)
    end
    return jwt, nil
end

local function validate_claims(claims)
    local now = ngx.time()

    -- Check expiration
    if claims.exp and claims.exp < now then
        return false, "Token has expired"
    end

    -- Check not before
    if claims.nbf and claims.nbf > now then
        return false, "Token not yet valid"
    end

    -- Check issuer
    if claims.iss and claims.iss ~= "flightschool-auth" then
        return false, "Invalid token issuer"
    end

    -- Check required claims
    if not claims.sub then
        return false, "Missing subject claim"
    end

    if not claims.org_id then
        return false, "Missing organization claim"
    end

    return true, nil
end

local function set_upstream_headers(claims)
    -- Set user context headers for downstream services
    kong.service.request.set_header("X-User-ID", claims.sub)
    kong.service.request.set_header("X-Organization-ID", claims.org_id)
    kong.service.request.set_header("X-User-Email", claims.email or "")
    kong.service.request.set_header("X-User-Name", claims.name or "")

    -- Set roles as comma-separated list
    if claims.roles and type(claims.roles) == "table" then
        kong.service.request.set_header("X-User-Roles", table.concat(claims.roles, ","))
    else
        kong.service.request.set_header("X-User-Roles", "")
    end

    -- Set permissions
    if claims.permissions and type(claims.permissions) == "table" then
        kong.service.request.set_header("X-User-Permissions", table.concat(claims.permissions, ","))
    end

    -- Set token metadata
    kong.service.request.set_header("X-Token-Issued-At", tostring(claims.iat or 0))
    kong.service.request.set_header("X-Token-Expires-At", tostring(claims.exp or 0))
end

local function error_response(status, code, message)
    local request_id = kong.request.get_header("X-Request-ID") or "unknown"

    return kong.response.exit(status, {
        error = {
            code = code,
            message = message,
            request_id = request_id,
            timestamp = ngx.utctime()
        }
    }, {
        ["Content-Type"] = "application/json",
        ["X-Request-ID"] = request_id
    })
end

-- =============================================================================
-- PLUGIN PHASES
-- =============================================================================

function FlightSchoolAuthHandler:access(conf)
    local path = kong.request.get_path()
    local method = kong.request.get_method()

    -- Skip auth for OPTIONS requests (CORS preflight)
    if method == "OPTIONS" then
        return
    end

    -- Skip auth for public paths
    if is_public_path(path) then
        kong.service.request.set_header("X-Auth-Type", "public")
        return
    end

    -- Get Authorization header
    local auth_header = kong.request.get_header("Authorization")
    local token, err = extract_token(auth_header)

    if err then
        return error_response(401, "UNAUTHORIZED", err)
    end

    -- Check token cache first
    local cache_key = "jwt:" .. ngx.md5(token)
    local cached_claims = kong.cache:get(cache_key)

    local claims
    if cached_claims then
        claims = cjson.decode(cached_claims)
    else
        -- Decode JWT
        local jwt, decode_err = decode_jwt(token)
        if decode_err then
            return error_response(401, "INVALID_TOKEN", decode_err)
        end

        claims = jwt.claims

        -- Validate claims
        local valid, validate_err = validate_claims(claims)
        if not valid then
            return error_response(401, "INVALID_TOKEN", validate_err)
        end

        -- Cache the claims
        local ttl = math.min(CACHE_TTL, (claims.exp or 0) - ngx.time())
        if ttl > 0 then
            kong.cache:set(cache_key, cjson.encode(claims), ttl)
        end
    end

    -- Set upstream headers
    set_upstream_headers(claims)
    kong.service.request.set_header("X-Auth-Type", "jwt")

    -- Store in context for logging
    kong.ctx.shared.user_id = claims.sub
    kong.ctx.shared.org_id = claims.org_id
    kong.ctx.shared.user_email = claims.email
end

function FlightSchoolAuthHandler:header_filter(conf)
    -- Add auth-related headers to response
    local user_id = kong.ctx.shared.user_id
    if user_id then
        kong.response.set_header("X-Authenticated-User", user_id)
    end
end

function FlightSchoolAuthHandler:log(conf)
    -- Log authentication info
    local user_id = kong.ctx.shared.user_id or "anonymous"
    local org_id = kong.ctx.shared.org_id or "none"

    kong.log.debug("Request by user: ", user_id, " org: ", org_id)
end

return FlightSchoolAuthHandler
