"""Job source fetchers registry."""

from jobhunter.sources.remoteok import RemoteOKSource
from jobhunter.sources.remotive import RemotiveSource
from jobhunter.sources.weworkremotely import WeWorkRemotelySource
from jobhunter.sources.jobicy import JobicySource
from jobhunter.sources.indeed import IndeedSource
from jobhunter.sources.linkedin import LinkedInSource

ALL_SOURCES = [
    RemoteOKSource,
    RemotiveSource,
    WeWorkRemotelySource,
    JobicySource,
    IndeedSource,
    LinkedInSource,
]

__all__ = [
    'ALL_SOURCES',
    'RemoteOKSource',
    'RemotiveSource',
    'WeWorkRemotelySource',
    'JobicySource',
    'IndeedSource',
    'LinkedInSource',
]
