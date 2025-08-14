"""Collection of Exceptions for the Edge Mining application domain."""
class DomainError(Exception):
    """Base class for domain-specific errors."""
    pass

class MinerError(DomainError):
    """Errors related to miners."""
    pass

class MinerNotFoundError(MinerError):
    """Miner not found."""
    pass

class MinerNotActiveError(MinerError):
    """Miner not active."""
    pass

class PolicyError(DomainError):
    """Errors related to optimization policies."""
    pass

class PolicyNotFoundError(PolicyError):
    """Optimization policy not found."""
    pass

class InvalidRuleError(PolicyError):
    """Invalid automation rule."""
    pass

class ConfigurationError(DomainError):
    """Errors related to system configuration."""
    pass
