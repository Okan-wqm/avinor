import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'relativeTime',
  standalone: true,
})
export class RelativeTimePipe implements PipeTransform {
  transform(value: string | Date): string {
    if (!value) return '';

    const now = new Date();
    const date = new Date(value);
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    // Future dates
    if (seconds < 0) {
      const absSeconds = Math.abs(seconds);
      if (absSeconds < 60) return 'in a few seconds';
      if (absSeconds < 3600) return `in ${Math.floor(absSeconds / 60)} minutes`;
      if (absSeconds < 86400) return `in ${Math.floor(absSeconds / 3600)} hours`;
      if (absSeconds < 604800) return `in ${Math.floor(absSeconds / 86400)} days`;
      return date.toLocaleDateString();
    }

    // Past dates
    if (seconds < 60) return 'just now';
    if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      return mins === 1 ? '1 minute ago' : `${mins} minutes ago`;
    }
    if (seconds < 86400) {
      const hours = Math.floor(seconds / 3600);
      return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
    }
    if (seconds < 604800) {
      const days = Math.floor(seconds / 86400);
      return days === 1 ? 'yesterday' : `${days} days ago`;
    }
    if (seconds < 2592000) {
      const weeks = Math.floor(seconds / 604800);
      return weeks === 1 ? '1 week ago' : `${weeks} weeks ago`;
    }

    return date.toLocaleDateString();
  }
}
