"""Disabled Windows launch contract. Only dependency-injected WinAPI simulations.

No native backend, subprocess API, network API or command-line entry exists.
Evidence from an adapter is trusted only as that adapter's observation, not as
proof of OS isolation. A real adapter and activation require a separate review.
"""
from dataclasses import dataclass
from hashlib import sha256
import ntpath
import re
from .projection import Hold

CREATE_SUSPENDED = 0x00000004


@dataclass(frozen=True)
class FixedLaunch:
    executable: str
    arguments: tuple[str, ...]
    image_sha256: str
    signer_sha256: str
    actor_sid: str
    timeout_seconds: int = 10
    enabled: bool = False


@dataclass(frozen=True)
class ImageEvidence:
    path: str
    file_id: str
    body: bytes
    signer_sha256: str
    signature_valid: bool
    owner_sid: str
    actor_sid: str
    owner_only: bool
    parents_safe: bool
    reparse_free: bool
    link_count: int
    deny_write_delete: bool


def _path(path):
    if (type(path) is not str or not re.fullmatch(r'[A-Za-z]:\\[^\x00-\x1f]+\.exe', path)
            or ntpath.normpath(path) != path or '/' in path or ':' in path[2:]
            or any(c in path for c in '"<>|?*')
            or any(part.endswith((' ', '.')) for part in path.split('\\'))):
        raise Hold('Canonical local absolute executable path required')


def _spec(spec):
    _path(spec.executable)
    if (spec.enabled is not False or type(spec.arguments) is not tuple
            or any(type(a) is not str or '\0' in a for a in spec.arguments)
            or type(spec.timeout_seconds) is not int or not 1 <= spec.timeout_seconds <= 10
            or not re.fullmatch(r'S-1-[0-9-]+', spec.actor_sid)):
        raise Hold('Disabled fixed launch contract required')
    for digest in (spec.image_sha256, spec.signer_sha256):
        if type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest):
            raise Hold('Fixed image and signer SHA256 required')


def _image(spec, evidence):
    if (evidence.path != spec.executable or not evidence.file_id
            or type(evidence.body) is not bytes
            or sha256(evidence.body).hexdigest() != spec.image_sha256
            or evidence.signer_sha256 != spec.signer_sha256
            or evidence.owner_sid != spec.actor_sid or evidence.actor_sid != spec.actor_sid
            or evidence.link_count != 1 or type(evidence.link_count) is not int
            or any(getattr(evidence, key) is not True for key in (
                'signature_valid', 'owner_only', 'parents_safe', 'reparse_free', 'deny_write_delete'))):
        raise Hold('Image bytes/signature/identity/ACL/lock verification failed')


def simulate_fixed_launch(spec, winapi, *, simulation=False):
    """Exercise a reviewed fixed request using a mock, never activate a real launch.

    Adapter obligations: hold a non-inheritable read handle denying write/delete;
    independently inspect process image bytes/signature/file ID; create a
    kill-on-close job with active-process limit 1, no breakaway; fail cleanup if
    termination cannot be confirmed. No live WinAPI adapter is shipped here.
    """
    _spec(spec)
    if simulation is not True or getattr(winapi, 'simulation_only', None) is not True:
        raise Hold('Only explicit synthetic WinAPI simulation is supported')
    image = job = process = None
    resumed = False
    try:
        image = winapi.lock_image(spec.executable, deny_write=True, deny_delete=True,
                                  inherit=False, reject_reparse=True)
        if image is None:
            raise Hold('No executable lock handle')
        before = winapi.inspect_file(image)
        _image(spec, before)
        job = winapi.create_job(kill_on_close=True, active_process_limit=1, breakaway=False)
        policy = winapi.job_policy(job)
        if (job is None or type(policy) is not tuple or len(policy) != 3
                or policy[0] is not True or type(policy[1]) is not int
                or policy[1] != 1 or policy[2] is not False):
            raise Hold('Child process containment unavailable')
        process = winapi.create_process(application_name=spec.executable,
            arguments=spec.arguments, creation_flags=CREATE_SUSPENDED,
            inherit_handles=False, actor_sid=spec.actor_sid)
        if process is None or winapi.is_suspended(process) is not True:
            raise Hold('Suspended creation not proven')
        winapi.assign_job(job, process)
        if winapi.job_members(job) != (process,):
            raise Hold('Unexpected child or job member')
        observed = winapi.inspect_process_image(process)
        _image(spec, observed)
        if observed.file_id != before.file_id:
            raise Hold('Process image was replaced')
        after = winapi.inspect_file(image)
        _image(spec, after)
        if after != before:
            raise Hold('Locked executable changed before resume')
        winapi.resume(process)
        resumed = True
        exit_code = winapi.wait(process, timeout_seconds=spec.timeout_seconds)
        if exit_code != 0 or type(exit_code) is not int or winapi.job_members(job):
            raise Hold('Process failed, timed out or descendants remain')
        return {'mode': 'synthetic_only', 'real_execution_authorized': False,
                'image_sha256': spec.image_sha256, 'image_verified': True,
                'exit_code': exit_code}
    except Exception as exc:
        if job is not None or process is not None:
            # Must kill the whole job, including failures after resume. This
            # acknowledgement is separate from closing handles or unblocking.
            if winapi.terminate_and_confirm(job, process) is not True:
                raise Hold('Termination unconfirmed; keep OS isolation in place') from exc
        raise Hold('Synthetic launch stopped' + (' after resume' if resumed else ' before resume')) from exc
    finally:
        winapi.close_handles(image, job, process)
