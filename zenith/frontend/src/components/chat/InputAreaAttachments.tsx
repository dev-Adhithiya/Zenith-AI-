import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';

interface InputAreaAttachmentsProps {
  imagePreviews: string[];
  onRemove: (index: number) => void;
}

/**
 * Image preview strip lives in its own component so `InputArea` stays focused on
 * send/voice/drag orchestration rather than thumbnail UI details.
 */
export function InputAreaAttachments({ imagePreviews, onRemove }: InputAreaAttachmentsProps) {
  return (
    <AnimatePresence>
      {imagePreviews.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mb-3 rounded-xl bg-white/5 border border-white/10 p-3"
        >
          <p className="text-xs text-white/50 mb-2 font-medium">
            {imagePreviews.length} image{imagePreviews.length !== 1 ? 's' : ''} selected
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {imagePreviews.map((preview, index) => (
              <motion.div
                key={`${preview}-${index}`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="relative group"
              >
                <img
                  src={preview}
                  alt={`Selected attachment preview ${index + 1}`}
                  className="w-full h-20 object-cover rounded-lg border border-white/10"
                />
                <motion.button
                  type="button"
                  onClick={() => onRemove(index)}
                  className="absolute top-1 right-1 p-1 rounded-md bg-red-500/80 text-white opacity-0 group-hover:opacity-100 transition-opacity focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  aria-label={`Remove image ${index + 1}`}
                >
                  <X className="w-4 h-4" />
                </motion.button>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
